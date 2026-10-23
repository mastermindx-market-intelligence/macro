"""Reproduce four exact-source Forex review INPUTS without browser/network work.

Uses the existing synthetic fixture, actual full template, page writer and asset
extractor. It neither renders live data nor creates a visual-acceptance receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
FONTS = {'.woff', '.woff2', '.ttf', '.otf', '.ttc', '.eot'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe relative path: {name!r}')
    return Path(*path.parts)


class DirectResources(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in ('script', 'img', 'source', 'iframe') and attrs.get('src'):
            self.urls.append(attrs['src'])
        if tag == 'link' and set(attrs.get('rel', '').split()) & {'stylesheet', 'icon', 'apple-touch-icon', 'preload', 'modulepreload'} and attrs.get('href'):
            self.urls.append(attrs['href'])


def resolve_url(value, parent=''):
    value = unquote(value.strip().strip('\"\'')); url = urlsplit(value)
    if url.scheme or url.netloc or not url.path or value.startswith('#'):
        return None
    name = posixpath.normpath(url.path.lstrip('/') if url.path.startswith('/') else posixpath.join(parent, url.path))
    safe_path(name)
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='A new, nonexistent directory')
    args = parser.parse_args(); repo = args.repo.resolve(strict=True); output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output already exists; nothing was overwritten.')
    spec = json.loads((HERE / 'SPEC.json').read_text()); revision = spec['source_commit']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Immutable source commit required')
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'}
    cache = {}; metadata = {}

    def git(*args):
        result = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args],
                                capture_output=True, env=env, timeout=45)
        if result.returncode:
            raise RuntimeError('Required local source object unavailable; no fetch attempted: ' + str(args))
        return result.stdout

    def object_info(path):
        safe_path(path)
        if path not in metadata:
            line = git('ls-tree', '-l', revision, '--', path).decode().strip()
            if not line:
                metadata[path] = None
            else:
                fields = line.split('\t', 1)[0].split()
                if len(fields) != 4 or fields[1] != 'blob':
                    raise RuntimeError('Expected a source file: ' + path)
                metadata[path] = {'source_path': path, 'git_blob_sha': fields[2], 'bytes': int(fields[3])}
        return metadata[path]

    def read_source(path):
        safe_path(path)
        if Path(path).suffix.lower() in FONTS:
            raise RuntimeError('Font binaries must not be read or copied by this utility.')
        if path not in cache:
            cache[path] = git('show', revision + ':' + path)
        return cache[path]

    for path, expected in spec['source_dependency_sha256'].items():
        if sha((repo / safe_path(path)).read_bytes()) != expected or sha(read_source(path)) != expected:
            raise RuntimeError('Wrong source dependency: ' + path)
    sys.path.insert(0, str(repo)); sys.dont_write_bytecode = True; os.chdir(repo)
    import pytest
    from jinja2 import Environment, FileSystemLoader
    from scripts import build_forex as BF
    from engine.i18n import tr, td
    from engine.forex_regime import fx_kinematics_table
    from lib import pages
    from scripts.externalize_css import externalize

    fixture_spec = importlib.util.spec_from_file_location('forex_review_source_fixture', repo / 'tests/test_forex_context_bus.py')
    fixture = importlib.util.module_from_spec(fixture_spec); fixture_spec.loader.exec_module(fixture)
    matched = fixture._r13_clock_table(); matched['rows'][0].update(lit_5d_pct=-.19, vel_z=1.51)
    different = copy.deepcopy(matched)
    different['rows'][0]['calculation_clock']['selected_index_dates']['lit_5d_pct'] = '2026-09-22'
    asset, drivers, cfg, _ = fixture._r14_asset('raw')
    raw = fx_kinematics_table({'USDJPY': asset}, drivers, cfg)
    tables = {'matched': matched, 'different_dates': different, 'unavailable': {}, 'raw_fallback': raw}
    original_dollar_vm = BF.dollar_vm
    loaded_templates = {}

    class ExactLoader(FileSystemLoader):
        def get_source(self, environment, template):
            text, filename, uptodate = super().get_source(environment, template)
            path = Path(filename).resolve(); relative = path.relative_to(repo).as_posix()
            if path.read_bytes() != read_source(relative):
                raise RuntimeError('Template source drift: ' + relative)
            loaded_templates[relative] = sha(path.read_bytes())
            return text, filename, uptodate

    output.mkdir(parents=True, exist_ok=False)
    source = {'review_input_schema': 1, 'source_commit': revision,
              'purpose': 'Controlled complete-route source INPUT, not live readings or visual evidence',
              'fixture_owner': 'tests/test_forex_context_bus.py::_r12_build_fixture / _r13_clock_table / _r14_asset',
              'pipeline': 'existing builder context -> actual Forex template -> lib.pages.write_page -> existing externalizer',
              'source_dependency_sha256': spec['source_dependency_sha256'],
              'fixed_build_label': spec['fixed_build_label'],
              'cases': {}, 'rendered_files': {}, 'assets': {}, 'font_assets_not_bundled': {},
              'browser_navigation_performed': False, 'server_started': False,
              'screenshot_acceptance': False, 'production_deployment': False,
              'runtime_dynamic_network_closure': 'NOT_PROVEN: shared scripts/session/data/external services and linked pages require separate admitted review.',
              'rebuild_command': 'python3 mockups/refs/forex_movement_r16_source_input/prepare.py --repo . --output /path/to/new-forex-review-input'}
    for case, table in tables.items():
        # Existing test seams prevent live data collection and durable state writers.
        with tempfile.TemporaryDirectory(prefix='forex-review-context-') as temp:
            with pytest.MonkeyPatch.context() as patch:
                snapshot, contexts = fixture._r12_build_fixture(Path(temp), patch, table)
                context = contexts[0]; context['dollar'] = original_dollar_vm(fixture._dol_frame())
                # The real builder inserts wall-clock text here. Bind the review
                # fixture explicitly instead of pretending it is a live build.
                context['built'] = spec['fixed_build_label']
                for section in context['sections']:
                    for pair in section['pairs']:
                        for factor in pair['conviction']['factors']:
                            factor['value'] = .4
                renderer = Environment(loader=ExactLoader(repo / 'templates'), autoescape=True)
                renderer.globals.update(tr=tr, td=td)
                html = renderer.get_template('forex.html.j2').render(**context)
        case_root = output / 'cases' / case; site = case_root / 'site'; site.mkdir(parents=True)
        pages._site_root = lambda: site; pages._shim_checked = False
        pages.write_page(site / 'forex.html', html, encoding='utf-8'); externalize(site)
        rendered = (site / 'forex.html').read_bytes()
        if sha(rendered) != spec['expected_html_sha256'][case]:
            raise RuntimeError('Full page differs from the frozen source-input probe: ' + case)
        (case_root / 'kinematics.json').write_text(json.dumps(snapshot['kinematics'], sort_keys=True, indent=2, allow_nan=False) + '\n')
        parser = DirectResources(); parser.feed(rendered.decode())
        queue = [(url, '') for url in parser.urls] + [(name, '') for name in spec['extra_shared_assets']]
        visited = set(); external = set()
        while queue:
            value, parent = queue.pop(0); name = resolve_url(value, parent)
            if name is None:
                if urlsplit(value).scheme not in ('', 'data'):
                    external.add(value)
                continue
            if name in visited:
                continue
            visited.add(name)
            if len(visited) > 256:
                raise RuntimeError('Unexpectedly broad static resource graph')
            target = site / safe_path(name)
            if target.is_file():
                data = target.read_bytes(); record = {'source_path': 'generated_by_existing_writer_or_extractor', 'bytes': len(data), 'sha256': sha(data)}
            else:
                origin = next((path for path in ('templates/' + name, 'site/' + name) if object_info(path)), None)
                if not origin:
                    raise RuntimeError('Unaccounted direct static resource: ' + name)
                if Path(name).suffix.lower() in FONTS:
                    source['font_assets_not_bundled'][name] = object_info(origin)
                    continue
                data = read_source(origin); record = {**object_info(origin), 'sha256': sha(data)}
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
            source['assets'][name] = record
            if name.endswith('.css'):
                queue.extend((url, str(PurePosixPath(name).parent)) for url in re.findall(r'url\(([^)]+)\)', data.decode()))
        source['cases'][case] = {'html_sha256': sha(rendered), 'html_bytes': len(rendered),
                                'component_css_sha256': sha((site / 'assets/css/b9b73065.css').read_bytes()),
                                'unresolved_direct_static_resources': [],
                                'external_direct_resource_urls_not_requested': sorted(external),
                                'fixture_not_live_data': True}

    checked_modules = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if path.suffix != '.py' or path.parent == HERE:
            continue
        if path.read_bytes() != read_source(relative):
            raise RuntimeError('Imported source drift: ' + relative)
        checked_modules[relative] = sha(path.read_bytes())
    source['loaded_template_sha256'] = loaded_templates
    source['imported_repo_module_sha256'] = checked_modules
    for path in sorted((output / 'cases').rglob('*')):
        if path.is_file():
            if path.suffix.lower() in FONTS:
                raise RuntimeError('Unexpected font output')
            data = path.read_bytes()
            source['rendered_files'][path.relative_to(output).as_posix()] = {'bytes': len(data), 'sha256': sha(data)}
    (output / 'SOURCE.json').write_text(json.dumps(source, sort_keys=True, indent=2) + '\n')
    for name in ['README.md', 'SPEC.json', 'prepare.py', 'verify_input.py']:
        (output / name).write_bytes((HERE / name).read_bytes())
    archive = output / 'candidate.zip'
    paths = sorted(path for path in output.rglob('*') if path.is_file())
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in paths:
            info = zipfile.ZipInfo(path.relative_to(output).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3; info.external_attr = 0o100644 << 16
            z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    print(json.dumps({'status': 'FOUR_SOURCE_INPUTS_NOT_BROWSER_PROOF', 'source': revision,
                      'zip_sha256': sha(archive.read_bytes()), 'zip_bytes': archive.stat().st_size,
                      'rendered_members': len(source['rendered_files']), 'font_binaries': 0,
                      'cases': source['cases'], 'imported_repo_modules_verified': len(checked_modules)}, sort_keys=True))


if __name__ == '__main__':
    main()
