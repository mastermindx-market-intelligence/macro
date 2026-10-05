"""Export and replay the uninstalled candidate patch against exact fixture copies.

The copy-only replay proves patch fidelity, not current-main compatibility or release.
It creates no Git branch/repository, touches no original source, and uses no data feed.
"""
from __future__ import annotations
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

HERE = Path(__file__).resolve().parent
OUT = HERE / ('rru_intl_complete_patch_20260910_' + a.PIN[:12])

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    OUT.mkdir(exist_ok=False)
    paths = sorted(candidate.bundle)
    prior = json.loads((HERE/'rru_force_patch_export_20260909_v2/manifest.json').read_text())
    expected_paths = set(prior['paths']) | {'templates/international_macro.html.j2', 'scripts/build_international_macro.py', 'engine/international_macro_dashboard.py'}
    assert set(paths) == expected_paths and len(paths) == 17
    original = {p: candidate.SOURCES[p].encode() for p in paths}
    expected = {p: candidate.edited[p].encode() for p in paths}
    def state(p):
        f = a.ROOT / p
        return f.read_bytes() if f.exists() else None
    before = {p: state(p) for p in paths}
    text = ''.join(''.join(difflib.unified_diff(original[p].decode().splitlines(True),
        expected[p].decode().splitlines(True), fromfile='a/'+p, tofile='b/'+p, n=0)) for p in paths)
    patch_path = OUT / 'candidate.patch'
    patch_path.write_text(text)
    manifest = dict(source_pin=a.PIN, capability='uninstalled_research_candidate',
        patch_format='unified_zero_context; exact before hashes required',
        paths={p:dict(before_sha256=sha(original[p]), after_sha256=sha(expected[p])) for p in paths},
        patch_sha256=sha(patch_path.read_bytes()), production=False, release_ready=False,
        remaining_release_gates=['independent full-candidate review', 'source custody and current integration', 'real-input applicability', 'installed-policy cutover', 'production publication and entitled browser proof'])
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='rru-force-copy-proof-', dir=HERE) as directory:
        root = Path(directory)
        for p, raw in original.items():
            f = root/p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(raw)
        run = subprocess.run(['/usr/bin/patch', '--batch', '-p1', '-i', str(patch_path)],
            cwd=root, text=True, capture_output=True, timeout=30, check=False)
        after = {p:sha((root/p).read_bytes()) for p in paths}
        exact = all(after[p] == sha(expected[p]) for p in paths)
        extras = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and str(p.relative_to(root)) not in paths)
    unchanged = all(state(p) == v for p,v in before.items())
    receipt = dict(patch_exit=run.returncode, files=len(paths), exact_candidate=exact,
        original_source_unchanged=unchanged, extra_files=extras,
        stdout=run.stdout, stderr=run.stderr, production=False, full_pipeline=False)
    (OUT/'replay-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt))
    return 0 if run.returncode == 0 and exact and unchanged and not extras else 1

if __name__ == '__main__':
    raise SystemExit(main())
