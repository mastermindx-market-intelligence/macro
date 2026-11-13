"""R11 research probe: selected functions from an immutable shared GMI candidate.

Default mode executes transcribed computational excerpts, NOT imported native modules.
--source-root additionally verifies full Git blobs and function ASTs against a checkout.
No production data, native writes, environment credentials, network, or code patch.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
import tempfile
from typing import Any
import yaml

CANDIDATE = '45eb37bbf832e007e67ce2594674d6bfeeb3b880'
SOURCES = {
    'engine/theme_graph/curation_assertion.py': '23a25614782b8b1cb76ce7e3f292b64d35bfb4f6',
    'engine/theme_graph/rights.py': '758937246e9a07ac150ba65123ebfa876bbc66c0',
}
# Functions retain computational statements; docstrings/comments are intentionally omitted.
# They were read through GitHub at CANDIDATE, not reconstructed from an inferred algorithm.
BLOCKS = {
'engine/theme_graph/curation_assertion.py': '''
def _check_authority(data: dict[str, Any]) -> None:
    auth = data.get("authority")
    if not isinstance(auth, Mapping):
        return
    for flag in AUTHORITY_FLAGS:
        if auth.get(flag) is not False:
            raise CurationAssertionError(
                f"authority_not_all_false: authority.{flag} must be literal false — "
                f"an assertion informs, it never ranks/gates/sizes/originates/opens")

def _check_observation(data: dict[str, Any]) -> None:
    obs = data.get("observation")
    if not isinstance(obs, Mapping):
        return
    for key in ("value", "value_high"):
        v = obs.get(key)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) \\
                or not math.isfinite(v) or v < 0:
            raise CurationAssertionError(
                f"observation_value_invalid: observation.{key} must be a finite "
                f"non-negative number (got {v!r})")
    if obs.get("value") is not None and obs.get("quantity_basis") is None:
        raise CurationAssertionError(
            "quantity_basis_required: observation.value carries no quantity_basis — "
            "a number nobody can say the basis of is not an observation")
''',
'engine/theme_graph/rights.py': '''
def _families_of(doc: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name, row in (doc.get("families") or {}).items():
        if isinstance(row, dict):
            out[str(name)] = row
    return out

def load_registry_snapshot(path: str | Path | None = None) -> tuple[str, dict[str, dict]]:
    p = Path(path) if path is not None else registry_path()
    if not p.exists():
        raise RightsRefusal(
            f"registry_missing: {p} does not exist — a missing registry refuses rather "
            f"than reading as all-clear")
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise RightsRefusal(f"registry_corrupt: {p} could not be read ({exc})") from exc
    revision = "rights_" + hashlib.sha256(data).hexdigest()[:32]
    try:
        doc = yaml.safe_load(data.decode("utf-8")) or {}
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RightsRefusal(
            f"registry_corrupt: {p} is not parseable YAML ({exc})") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("families"), dict):
        raise RightsRefusal(
            f"registry_corrupt: {p} carries no top-level `families` mapping — an "
            f"unreadable registry refuses rather than defaults")
    return (revision, _families_of(doc))

def assert_current_emission_allowed(families: Iterable[str], *,
                                    snapshot: tuple[str, dict[str, dict]]) -> None:
    revision, registry = snapshot
    for family in families:
        name = str(family or "").strip()
        row = registry.get(name)
        if row is None:
            raise RightsRefusal(
                f"unknown_family:{name} — source family {name!r} has no row in rights "
                f"snapshot {revision} — rights are STATED, never assumed")
        cls = str(row.get("rights_class", "")).strip()
        if cls not in RIGHTS_CLASSES:
            raise RightsRefusal(
                f"public emission refused for source family {name!r}: rights_class="
                f"{cls!r}, outside {sorted(RIGHTS_CLASSES)} (snapshot {revision}) — an "
                f"unreadable class refuses rather than defaults")
        if cls not in EMISSION_OK:
            raise RightsRefusal(
                f"public emission refused for source family {name!r}: rights_class="
                f"{cls!r} (snapshot {revision}; permitted: {sorted(EMISSION_OK)}). "
                f"Internal computation is unaffected — this gate governs what leaves "
                f"the house")
''',
}

class CurationAssertionError(ValueError):
    pass
class RightsRefusal(RuntimeError):
    pass

AUTHORITY_FLAGS = ('can_rank', 'can_gate', 'can_size', 'can_originate', 'can_open_entry')
RIGHTS_CLASSES = frozenset({'internal_only', 'derived_display_ok', 'direct_display_ok', 'unresolved'})
EMISSION_OK = frozenset({'derived_display_ok', 'direct_display_ok'})

def _without_docstrings(node: ast.AST) -> ast.AST:
    result = copy.deepcopy(node)
    for item in ast.walk(result):
        if isinstance(item, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if item.body and isinstance(item.body[0], ast.Expr) and isinstance(item.body[0].value, ast.Constant) and isinstance(item.body[0].value.value, str):
                item.body.pop(0)
    return result

def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def verify_source_root(root: Path) -> dict:
    receipts = {}
    for path, expected in SOURCES.items():
        data = (root/path).read_bytes()
        actual = _git_blob(data)
        if actual != expected:
            raise ValueError(f'{path}: candidate changed ({actual}); requalify, do not bypass the pin')
        native = {n.name:n for n in ast.parse(data).body if isinstance(n, ast.FunctionDef)}
        for node in ast.parse(BLOCKS[path]).body:
            if ast.dump(_without_docstrings(native[node.name])) != ast.dump(_without_docstrings(node)):
                raise ValueError(f'{path}::{node.name}: excerpt AST differs from native function')
        receipts[path] = {'git_blob':actual, 'selected_function_ast_match':True}
    # Execution uses only the selected function code below, even in source-root mode.
    return receipts

def run(source_root: Path | None) -> dict:
    native_verification = verify_source_root(source_root) if source_root else None
    namespace = dict(globals())
    for path, code in BLOCKS.items():
        tree = ast.parse(code)
        if not all(isinstance(n, ast.FunctionDef) for n in tree.body):
            raise ValueError('excerpt must contain only approved function definitions')
        exec(compile(tree,path+'#selected-functions','exec'),namespace)
    rows = []
    def test(case_id, fn, expected, scope, requirement_met=None):
        try:
            result = fn()
            observed = 'allowed' if result is None else result
        except (CurationAssertionError,RightsRefusal) as exc:
            observed = str(exc).split(':',1)[0]
        matched = observed == expected
        rows.append({'id':case_id,'expected':expected,'observed':observed,'matched':matched,
                     'scope':scope,'materials_requirement_met':requirement_met})
    check = namespace['_check_observation']
    def observation(value, high=None, basis='per_unit'):
        return {'predicate':'REPORTED_FINANCIAL_MEASURE',
                'observation':{'value':value,'value_high':high,'quantity_basis':basis}}
    test('M01_positive_number',lambda:check(observation(781)),'allowed','Quantity semantic helper only.',True)
    test('M02_negative_financial',lambda:check(observation(-31)),'observation_value_invalid','Financial predicate does not bypass nonnegative quantity rule.',False)
    test('M03_exact_decimal_text',lambda:check(observation('781.000000000000000001')),'observation_value_invalid','Exact decimal-text values have no supported observation branch.',False)
    test('M04_zero',lambda:check(observation(0)),'allowed','Measured zero is not absence.',True)
    test('M05_unknown',lambda:check(observation(None)),'allowed','Helper preserves absence; outer schema still required.',True)
    test('M06_boolean',lambda:check(observation(True)),'observation_value_invalid','Boolean is not a numeric measurement.',True)
    test('M07_infinity',lambda:check(observation(float('inf'))),'observation_value_invalid','Non-finite number refused.',True)
    test('M08_negative_high',lambda:check(observation(None,-1)),'observation_value_invalid','Range upper value follows same sign restriction.',None)
    test('M09_missing_basis',lambda:check(observation(5,basis=None)),'quantity_basis_required','Known value without basis refused.',True)
    test('M10_fractional_quantity',lambda:check(observation(0.5)),'allowed','Continuous physical quantity already fits numeric helper; do not classify all quantities as integer counts.',True)
    auth = namespace['_check_authority']
    test('A01_all_false',lambda:auth({'authority':dict.fromkeys(AUTHORITY_FLAGS,False)}),'allowed','Authority helper only.',True)
    test('A02_rank_true',lambda:auth({'authority':{**dict.fromkeys(AUTHORITY_FLAGS,False),'can_rank':True}}),'authority_not_all_false','Research cannot self-grant rank authority.',True)
    test('A03_rank_zero',lambda:auth({'authority':{**dict.fromkeys(AUTHORITY_FLAGS,False),'can_rank':0}}),'authority_not_all_false','Literal false, not numeric zero.',True)
    load = namespace['load_registry_snapshot']; gate = namespace['assert_current_emission_allowed']
    with tempfile.TemporaryDirectory(prefix='materials-r11-') as d:
        p=Path(d)/'policy.yml'
        permitted=b'families:\n  fixture:\n    rights_class: derived_display_ok\n'
        p.write_bytes(permitted); before=load(p)
        test('R01_initial_allow',lambda:gate(['fixture'],snapshot=before),'allowed','Synthetic registry.',True)
        test('R02_digest_of_parsed_bytes',lambda:before[0]=='rights_'+hashlib.sha256(permitted).hexdigest()[:32],True,'Revision identifies the bytes loaded by the snapshot.',True)
        p.write_bytes(b'families:\n  fixture:\n    rights_class: internal_only\n'); after=load(p)
        test('R03_reread_observes_revocation',lambda:gate(['fixture'],snapshot=after),'public emission refused for source family \'fixture\'','Fresh API, same process/path; no cache clearing.',True)
        test('R04_revision_changes',lambda:before[0]!=after[0],True,'Two policy contents have different snapshot revisions.',True)
        test('R05_old_snapshot_still_allows',lambda:gate(['fixture'],snapshot=before),'allowed','Callers must re-read at response boundary; old snapshot is not a revocation oracle.',None)
        test('R06_unknown_family',lambda:gate(['not_registered'],snapshot=after),'unknown_family','Unknown source family refused.',True)
        test('R07_empty_family_control',lambda:gate([],snapshot=after),'allowed','Complete input-to-family derivation is a caller obligation, not proven by empty list.',None)
        p.write_bytes(b'families:\n  fixture:\n    rights_class: typo\n'); invalid=load(p)
        test('R08_unknown_class',lambda:gate(['fixture'],snapshot=invalid),'public emission refused for source family \'fixture\'','Unknown rights class refused.',True)
        p.write_bytes(b'families: [invalid, shape]\n')
        test('R09_invalid_shape',lambda:load(p),'registry_corrupt','Malformed policy does not become empty evidence.',True)
        p.write_bytes(b'families: [\n')
        test('R10_bad_yaml',lambda:load(p),'registry_corrupt','Unparseable YAML refused.',True)
        p.write_bytes(b'\xff')
        test('R11_bad_utf8',lambda:load(p),'registry_corrupt','Non-UTF8 input refused.',True)
        p.unlink()
        test('R12_missing_file',lambda:load(p),'registry_missing','Missing registry distinct from successful empty evidence.',True)
    result = {
        'scope':'Selected-function research compatibility probe; not full schema/module/API/store/browser tests or production acceptance.',
        'candidate_commit':CANDIDATE,'source_git_blobs':SOURCES,
        'execution_mode':'source_blob_and_function_ast_verified' if native_verification else 'transcribed_computational_excerpts_only',
        'full_native_file_verification':native_verification,
        'excerpts_sha256':{p:hashlib.sha256(c.encode()).hexdigest() for p,c in BLOCKS.items()},
        'checks':rows,'matching_observations':sum(x['matched'] for x in rows),
        'observation_mismatches':sum(not x['matched'] for x in rows),
        'unmet_materials_requirements':[x['id'] for x in rows if x['materials_requirement_met'] is False],
        'native_data_read':False,'native_data_written':False,'product_code_modified':False,'decision_authority':False,
        'limitations':['No full native import or complete schema roundtrip in this run.',
                      'No deployed caller, final response recheck, original-source rights coverage or entitlement proof.',
                      'Compatibility gaps remain failures to meet Materials requirements, even when expected observations match.']}
    if result['observation_mismatches']:
        raise AssertionError(json.dumps(result,indent=2))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    result=run(args.source_root)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as f: f.write(text)
    else: print(text,end='')

if __name__=='__main__': main()
