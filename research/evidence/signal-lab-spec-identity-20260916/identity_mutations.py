"""Fault-inject one source module in memory; never edit the source under test."""
from __future__ import annotations
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
CASES = {
 "source_omitted": ("engine.signal_foundry.spec", '"data": data,', '"data": [],',
                     "test_identity_changes_when_computation_input_changes[input_path]"),
 "baseline_omitted": ("engine.signal_foundry.spec", '"baseline": spec.get("baseline", "buy_and_hold"),',
                       '"baseline": "buy_and_hold",', "test_identity_changes_when_computation_input_changes[baseline]"),
 "complete_legacy_not_projected": ("engine.signal_foundry.screen", "if complete:", "if False:",
                                   "test_full_legacy_collision_does_not_reject_different_inputs"),
 "prior_history_ignored": ("engine.signal_foundry.screen", 'text = path.read_text(encoding="utf-8")',
                           'text = ""', "test_legacy_proposed_record_without_hash_still_prevents_duplicate"),
 "corrupt_line_ignored": ("engine.signal_foundry.screen",
                         'raise ValueError(f"invalid prior candidate JSON at line {line_no}") from exc',
                         'continue', "test_corrupt_prior_registry_cannot_silently_admit"),
 "backend_hash_spoofed": ("scripts.run_signal_foundry_brainstorm",
                         'spec["construction_hash"] = construction_hash(spec)',
                         'spec["construction_hash"] = "invented"',
                         "test_brainstorm_filer_overwrites_spoof_and_rejects_same_batch_rename"),
 "invalid_definition_written": ("scripts.run_signal_foundry_brainstorm",
                        '**(spec if "construction_hash" in spec else {"identity_error": "construction_not_canonical_json"}),',
                        '**spec,', "test_malformed_rejection_cannot_poison_future_novelty[brainstorm]"),
 "backend_version_spoofed": ("scripts.codex_signal_lane", 'construction_hash_version=CONSTRUCTION_HASH_VERSION)',
                            'construction_hash_version=999)',
                            "test_codex_filing_helper_uses_backend_identity_without_provider"),
}


def run_child(case: str, output: Path) -> int:
    name, before, after, test = CASES[case]
    path = ROOT / (name.replace(".", "/") + ".py")
    original = path.read_text()
    assert original.count(before) == 1, (case, 'fault anchor not unique')
    injected = original.replace(before, after, 1)
    class Loader(importlib.abc.Loader):
        def create_module(self, spec): return None
        def exec_module(self, module):
            module.__file__ = str(path)
            exec(compile(injected, str(path), "exec"), module.__dict__)
    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == name:
                return importlib.util.spec_from_loader(fullname, Loader())
    sys.path.insert(0, str(ROOT))
    sys.meta_path.insert(0, Finder())
    import pytest
    return pytest.main([f"tests/test_sf_spec_identity.py::{test}",
                        f"--basetemp={output / (case + '-tmp')}",
                        f"--junitxml={output / (case + '.xml')}", '-q', '--tb=short'])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--case', choices=list(CASES))
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    if not output.is_relative_to((ROOT / '.pytest_cache').resolve()):
        parser.error('output must be inside this worktree test cache')
    if args.case:
        raise SystemExit(run_child(args.case, output))
    if output.exists():
        parser.error('use a new output directory; prior evidence is immutable')
    output.mkdir(parents=True)
    paths = sorted({name.replace('.', '/') + '.py' for name, _, _, _ in CASES.values()})
    hashes = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    results = []
    for case in CASES:
        command = [sys.executable, str(Path(__file__).resolve()), '--output', str(output), '--case', case]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90)
        log = output / (case + '.log'); log.write_text(proc.stdout + proc.stderr)
        xml = output / (case + '.xml')
        suites = ET.parse(xml).getroot().findall('testsuite') if xml.exists() else []
        failures = sum(int(x.get('failures', 0)) for x in suites)
        errors = sum(int(x.get('errors', 0)) for x in suites)
        result = {'case':case, 'exit_code':proc.returncode, 'assertion_failures':failures,
                  'errors':errors, 'caught':proc.returncode == 1 and failures > 0 and errors == 0,
                  'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
        results.append(result); print(json.dumps(result), flush=True)
    unchanged = hashes == {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    receipt = {'source_sha256':hashes, 'source_unchanged':unchanged, 'cases':results,
               'all_caught':all(x['caught'] for x in results), 'production_proven':False}
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    assert unchanged and receipt['all_caught'], receipt


if __name__ == '__main__':
    main()
