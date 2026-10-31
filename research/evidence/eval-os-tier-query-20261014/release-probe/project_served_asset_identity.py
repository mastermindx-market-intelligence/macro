"""Project public bytes from a qualified explicit revision, without serving them."""
import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import threading

REVIEWED_SERVER_AST = {'_STATIC_ASSET_NAMES': '44f9389157694846d57aee7df0b23ee0de0802ae07e5a570cfbe39370d02ffec', '_STATIC_ASSET_VERSIONS': '22b47778f4d872117878fa10e2a6afdef57f50bff211fedb499c1c318941eb4a', '_theme_token_asset': '74b96acc9d8714ba013ac4481d0100a9371fe0e08c6019da930fc7c3ef32864e', '_static_body': 'a0a6bbc9140a16ad23be49667a52c3a98b5ba953978774e6e7ebf9b506398496'}
REVIEWED_TOKEN_PROJECTOR = '1e27b1decad0273a3a495e7151be8ba22a03e131761ceeb93da065af1693cf46'
SOURCE_PATHS = ('admin/server.py', 'admin/theme_tokens.py', 'templates/theme.css',
                'admin/static/index.html', 'admin/static/app.js',
                'admin/static/styles.css', 'admin/static/preferences.js')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], timeout=30)


def project(repo, revision, destination):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Use an exact full commit SHA, after independent qualification')
    if git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('Not the identified commit')
    if destination.exists():
        raise ValueError('Destination must be new; preserve earlier evidence')
    blobs = {}
    for name in SOURCE_PATHS:
        entry = git(repo, 'ls-tree', revision, '--', name).decode().strip()
        metadata, actual_name = entry.split('\t', 1)
        mode, kind, oid = metadata.split()
        if actual_name != name or mode not in ('100644', '100755') or kind != 'blob':
            raise ValueError('Expected a regular source blob')
        size = int(git(repo, 'cat-file', '-s', oid))
        if not 0 < size <= 4 * 1024 * 1024:
            raise ValueError('Source size outside 4 MiB bound')
        blobs[name] = git(repo, 'cat-file', 'blob', oid)
        if len(blobs[name]) != size:
            raise ValueError('Source size changed')
    if digest(blobs['admin/theme_tokens.py']) != REVIEWED_TOKEN_PROJECTOR:
        raise ValueError('Token projector changed; review before executing it')
    syntax = ast.parse(blobs['admin/server.py'])
    nodes = {}
    for node in syntax.body:
        names = [node.name] if isinstance(node, ast.FunctionDef) else [t.id for t in getattr(node, 'targets', []) if isinstance(t, ast.Name)]
        for name in names:
            if name in REVIEWED_SERVER_AST:
                if digest(ast.dump(node, include_attributes=False).encode()) != REVIEWED_SERVER_AST[name]:
                    raise ValueError('Server asset contract changed; review required: ' + name)
                nodes[name] = node
    if set(nodes) != set(REVIEWED_SERVER_AST):
        raise ValueError('Server asset contract incomplete')
    token_ns = {}
    exec(compile(blobs['admin/theme_tokens.py'], 'reviewed-token-projector', 'exec'), token_ns)
    tokens = token_ns['project_theme_tokens'](blobs['templates/theme.css'].decode()).encode()
    class Blob:
        def __init__(self, key):
            self.key = key
        def __truediv__(self, other):
            return Blob(self.key + '/' + other)
        def is_file(self):
            return self.key in blobs
        def read_bytes(self):
            return blobs[self.key]
    namespace = {'STATIC': Blob('admin/static'), 'hashlib': hashlib,
                 '_STATIC_BODY_CACHE': {}, '_STATIC_BODY_LOCK': threading.RLock(),
                 '_theme_token_asset': lambda: (tokens, digest(tokens)[:12])}
    selected = ast.Module(body=[nodes['_STATIC_ASSET_NAMES'], nodes['_STATIC_ASSET_VERSIONS'], nodes['_static_body']], type_ignores=[])
    exec(compile(selected, 'reviewed-server-asset-functions', 'exec'), namespace)
    assets = {name: blobs['admin/static/' + name] for name in namespace['_STATIC_ASSET_NAMES']}
    assets['assets/theme-tokens.css'] = tokens
    index = namespace['_static_body']('index.html', Blob('admin/static/index.html'))
    receipt = {'schema': 'eval_os.expected_public_assets.v1', 'candidate': revision,
               'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'assets': {name: {'sha256': digest(data), 'bytes': len(data)} for name, data in assets.items()},
               'expected_served_index_sha256': digest(index),
               'source_sha256': {name: digest(data) for name, data in blobs.items()},
               'reviewed_server_ast': REVIEWED_SERVER_AST,
               'tool_sha256': digest(Path(__file__).read_bytes()),
               'scope': 'Offline expected bytes only. No server import, credentials, network service, API, installation or served-production observation. Qualification and merge are independent prerequisites.'}
    destination.mkdir(exist_ok=False)
    (destination / 'expected-served-assets.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (destination / 'expected-served-index.html').write_bytes(index)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    receipt = project(args.repo, args.source_commit, args.destination)
    print(json.dumps({'candidate': receipt['candidate'], 'assets': receipt['assets'], 'expected_served_index_sha256': receipt['expected_served_index_sha256'], 'scope': receipt['scope']}, indent=2))
