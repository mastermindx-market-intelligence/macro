"""Rebuild the immutable Bonds review INPUT using existing repository renderers.

No server, browser, font redistribution, network request, Git write or acceptance
receipt. Requires the recorded source objects and the repository's existing Python
render/test dependencies locally. A changed source dependency fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
FONT_SUFFIXES = {'.woff', '.woff2', '.ttf', '.otf', '.eot', '.ttc'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative(value: str) -> Path:
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe archive/source path: {value!r}')
    return Path(*path.parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path, help='Existing checkout with exact recorded source dependencies')
    parser.add_argument('--output', required=True, type=Path, help='New output directory; existing paths are never overwritten')
    args = parser.parse_args()
    repo = args.repo.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise SystemExit('Output already exists. Supply a new directory; nothing was overwritten.')
    source = json.loads((HERE / 'SOURCE.json').read_text())
    revision = source['source_commit']
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise SystemExit('Source must be an immutable 40-character Git commit.')
    env = {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_TERMINAL_PROMPT': '0'}

    def git_bytes(name: str) -> bytes:
        safe_relative(name)
        result = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), 'show', f'{revision}:{name}'],
                                capture_output=True, env=env, timeout=45)
        if result.returncode:
            raise RuntimeError(f'Required local source object unavailable: {name}. No fetch was attempted.')
        return result.stdout

    for name, expected in source['source_dependency_sha256'].items():
        local = repo / safe_relative(name)
        if digest(local.read_bytes()) != expected or digest(git_bytes(name)) != expected:
            raise RuntimeError(f'Wrong source dependency: {name}')

    # Assets come from the immutable source object, never current site output.
    asset_bytes = {}
    for name, record in source['assets'].items():
        safe_relative(name)
        if Path(name).suffix.lower() in FONT_SUFFIXES:
            raise RuntimeError('Font redistribution is not permitted.')
        path = record['source_path']
        if path == 'generated_by_existing_writer_or_extractor':
            continue
        if Path(path).suffix.lower() in FONT_SUFFIXES:
            raise RuntimeError('Font source cannot be copied.')
        data = git_bytes(path)
        if len(data) != record['bytes'] or digest(data) != record['sha256']:
            raise RuntimeError(f'Asset identity mismatch: {name}')
        asset_bytes[name] = data

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    from jinja2 import Environment, FileSystemLoader
    from lib import pages
    from scripts.externalize_css import externalize

    fixture_path = repo / 'tests/test_bonds_divergence_gate.py'
    spec = importlib.util.spec_from_file_location('bonds_review_input_fixture', fixture_path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    context = fixture._base_ctx()

    # Check imported repository Python code too; standard/third-party libraries
    # remain the existing environment dependencies, not a bundled runtime.
    checked = set()
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        path = Path(filename).resolve()
        try:
            relative = path.relative_to(repo)
        except ValueError:
            continue
        if path.suffix != '.py' or path.parent == HERE or relative.as_posix() in checked:
            continue
        if path.read_bytes() != git_bytes(relative.as_posix()):
            raise RuntimeError(f'Imported source drift: {relative}')
        checked.add(relative.as_posix())

    output.mkdir(parents=True, exist_ok=False)
    site = output / 'site'; site.mkdir()
    pages._site_root = lambda: site
    pages._shim_checked = False
    renderer = Environment(loader=FileSystemLoader(repo / 'templates'), autoescape=True)
    html = renderer.get_template('bonds.html.j2').render(**context)
    pages.write_page(site / 'bonds.html', html, encoding='utf-8')
    externalize(site)
    for name, data in asset_bytes.items():
        target = site / safe_relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError(f'Generated/source asset collision: {name}')
        target.write_bytes(data)

    actual = {str(path.relative_to(output)): path.read_bytes() for path in site.rglob('*') if path.is_file()}
    if set(actual) != set(source['rendered_files']):
        raise RuntimeError(f'Output member mismatch: {sorted(set(actual) ^ set(source["rendered_files"]))}')
    for name, data in actual.items():
        expected = source['rendered_files'][name]
        if len(data) != expected['bytes'] or digest(data) != expected['sha256']:
            raise RuntimeError(f'Rendered bytes differ: {name}')
        if Path(name).suffix.lower() in FONT_SUFFIXES:
            raise RuntimeError('Unexpected font output.')
    if digest(actual['site/bonds.html']) != source['html_sha256']:
        raise RuntimeError('Full HTML differs from the accepted source input.')

    for name in ['SOURCE.json', 'README.md', 'rebuild.py', 'verify_input.py']:
        actual[name] = (HERE / name).read_bytes()
        (output / name).write_bytes(actual[name])
    archive_path = output / 'candidate.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(actual):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, actual[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    print(json.dumps({'status': 'SOURCE_INPUT_REBUILT_NOT_BROWSER_PROOF', 'source_commit': revision,
                      'html_sha256': source['html_sha256'], 'rendered_files': len(source['rendered_files']),
                      'archive_sha256': digest(archive_path.read_bytes()), 'archive_bytes': archive_path.stat().st_size,
                      'imported_repo_modules_verified': len(checked), 'font_binaries': 0,
                      'browser_started': False, 'server_started': False, 'output': str(output)}, sort_keys=True))


if __name__ == '__main__':
    main()
