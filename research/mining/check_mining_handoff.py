"""Check a preserved planning packet; never execute product or source-admission tests.
Run from a checkout or this portable tree: python research/mining/check_mining_handoff.py
Standard library only. Writes the adjacent verification receipt, with actual run time.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = 'docs/superpowers/specs/2026-09-24-mining-shared-foundation-economic-dossier-design.md'
PLAN = 'docs/superpowers/plans/2026-09-24-mining-economic-dossier-implementation.md'
QUAL = 'research/mining/MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md'
TRACE = 'research/mining/MINING_IMPLEMENTATION_TRACE_2026-09-24.json'
ADDENDUM = 'docs/superpowers/plans/2026-09-24-mining-integration-plan-addendum.md'
PACKET = 'agentos/handoffs/GMI-MINING-MASTER-FABLE-CEO-HANDOFF-2026-09-24.md'
FROZEN = {
    SPEC: '33d9448142d1ce922201b9938ae755b6239ea1e2',
    PLAN: 'a2fca1c561b799b7e49d69c9095e5ffa7dd094cc',
    QUAL: '34548e6b874148e017ec9b4efb7566c3e94123c8',
    TRACE: '37ccaa92c301667b176be80c3fa6fbdcece72665',
}
EXCLUDED_P05 = '587ee020adec174233c42ad987f531d767b7c0ea'
CANONICAL_P05 = '42c90b4634b4b408c014b7ccb335744adb79bf48'


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def inspect(files: dict[str, bytes]) -> dict[str, bool]:
    spec = files[SPEC].decode('utf-8')
    plan = files[PLAN].decode('utf-8')
    packet = files[PACKET].decode('utf-8')
    addendum = files[ADDENDUM].decode('utf-8')
    trace = json.loads(files[TRACE])
    rows = trace['requirements']
    expected = [f'MGD-{i:02}' for i in range(1, 41)]
    source_rows = dict(re.findall(r'^\| (MGD-\d{2}) \| [^|]+ \| (.*?) \|$', spec, re.M))
    checks = {f'frozen:{name}': blob(files[name]) == expected_blob for name, expected_blob in FROZEN.items()}
    checks.update({
        'forty_obligations_retained': [r['id'] for r in rows] == expected,
        'verbatim_spec_obligations': all(r['requirement'] == source_rows.get(r['id']) for r in rows),
        'all_product_tests_unrun': all(r['execution'] == 'NOT_RUN' for r in rows),
        'eight_tasks_resolve': trace['task_ids'] == [f'T{i:02}' for i in range(1,9)] and all(r['task'] in trace['task_ids'] for r in rows),
        'future_test_references_retained': all(r['test'] in plan for r in rows),
        'prepared_not_build_ready': 'BUILD_READY: false' in packet and 'DISPATCHED_BY_THIS_PACKET: false' in packet,
        'receiver_unassigned': 'RECEIVER: none assigned by this packet' in packet and 'PLACEMENT_STATE: WAITING_CAPACITY / needs_placement' in packet,
        'two_positive_witnesses': '### W-C ' in packet and '### W-R ' in packet,
        'eight_corpus_passes': len(re.findall(r'^\| P0[1-8] \|', packet, re.M)) == 8,
        'duplicate_explicitly_excluded': CANONICAL_P05 in packet and EXCLUDED_P05 in packet and 'DO_NOT_PUBLISH_DUPLICATE' in packet,
        'no_excluded_P05_bytes': all(blob(raw) != EXCLUDED_P05 for raw in files.values()),
        'upstream_only_T01': '**Replacement assignment for T01:** consume' in addendum and 'Mining worker\'s assignment to implement the base' in addendum,
        'definition_warning_not_acceptance': 'definition_unqualified:<field>' in addendum and 'No favorable badge' in addendum,
        'answered_vs_pending_distinguished': '5809602368' in addendum and '5809893850' in addendum and 'open in exact implementation' in addendum,
        'version_extension_not_enrolled': 'theme_graph.curation_assertion.v1.1' in addendum and 'not permission to widen' in addendum,
        'source_use_not_blanket_government_work': 'https://www.usa.gov/government-copyright' in addendum and 'not as a ruling that every filing fact is restricted' in addendum,
        'seven_original_gates_retained': len(re.findall(r'^\| G[1-7] ', addendum, re.M)) == 7,
        'full_mission_retained': 'M1 acceptance does not complete the full Mining intelligence program' in packet,
    })
    return checks


def main() -> None:
    paths = [SPEC, PLAN, QUAL, TRACE, ADDENDUM, PACKET]
    files = {path: (ROOT / path).read_bytes() for path in paths}
    checks = inspect(files)
    mutations = {}
    changed = dict(files)
    tr = copy.deepcopy(json.loads(files[TRACE])); tr['requirements'].pop()
    changed[TRACE] = json.dumps(tr).encode()
    mutations['missing_MGD_40_rejected'] = not inspect(changed)['forty_obligations_retained']
    changed = dict(files); changed[PACKET] = files[PACKET].replace(b'BUILD_READY: false', b'BUILD_READY: true')
    mutations['false_build_readiness_rejected'] = not inspect(changed)['prepared_not_build_ready']
    changed = dict(files); changed[ADDENDUM] = files[ADDENDUM].replace(b'**Replacement assignment for T01:** consume', b'**Replacement assignment for T01:** build')
    mutations['base_build_assignment_rejected'] = not inspect(changed)['upstream_only_T01']
    changed = dict(files); changed[PLAN] += b'\nUnreviewed plan change\n'
    mutations['changed_original_plan_rejected'] = not inspect(changed)[f'frozen:{PLAN}']
    tr = copy.deepcopy(json.loads(files[TRACE])); tr['requirements'][0]['execution'] = 'PASS'
    changed = dict(files); changed[TRACE] = json.dumps(tr).encode()
    mutations['invented_product_pass_rejected'] = not inspect(changed)['all_product_tests_unrun']
    receipt = {
        'operation': 'gmi-mining-principal-research-20260923-sol-001',
        'classification': 'PLANNING_PACKAGE_INTEGRITY_AND_ADMISSION_LABELS_ONLY',
        'run_utc': datetime.now(timezone.utc).isoformat(),
        'command': 'python research/mining/check_mining_handoff.py',
        'passed': sum(checks.values()), 'failed': sum(not x for x in checks.values()),
        'checks': checks, 'mutations_rejected': mutations,
        'documents': {p: {'bytes': len(raw), 'words': len(raw.decode().split()), 'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob_sha1': blob(raw)} for p, raw in files.items()},
        'checker_git_blob_sha1': blob(Path(__file__).read_bytes()),
        'not_claimed': ['native product tests', 'upstream module execution', 'independent review', 'source admission', 'source rights grant', 'receiver assignment', 'START', 'CI', 'merge', 'deployment', 'browser proof', 'investment validation'],
    }
    output = ROOT / 'research/mining/MINING_HANDOFF_REVIEW_CHECKS_2026-09-24.json'
    output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': receipt['passed'], 'failed': receipt['failed'], 'mutations': mutations, 'receipt_blob': blob(output.read_bytes()), 'checker_blob': receipt['checker_git_blob_sha1']}, indent=2))
    if not all(checks.values()) or not all(mutations.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
