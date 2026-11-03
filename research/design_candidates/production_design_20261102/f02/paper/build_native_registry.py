#!/usr/bin/env python3
"""Bind source preparation to observed Paper IDs; never infer a native ID.

Run from the workspace root after the exclusive writer saves its runtime.
Outputs are projections, not approvals or a substitute for final live readback.
"""
from pathlib import Path
import copy
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
PAPER = ROOT / 'paper'


def read(path):
    return json.loads(path.read_text())


def save(name, value):
    (PAPER / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def file_receipt(path):
    if not path.exists():
        return None
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest()}


def main():
    runtime_path = PAPER / 'writer-continuation-progress.json'
    if not runtime_path.exists():
        runtime_path = PAPER / 'native-progress.json'
    runtime = read(runtime_path)
    by_key = {b['key']: b for b in runtime['boards']}
    assert len(by_key) == len(runtime['boards']), 'duplicate native board key'
    assert len({b['id'] for b in by_key.values()}) == len(by_key)
    now = datetime.now(timezone.utc).isoformat()
    captures = runtime.get('captures', [])
    retention_path = PAPER / 'native-final-retention.json'
    retention = read(retention_path) if retention_path.exists() else None
    retained_by_id = {(r['file_id'], r['board_id']): r for r in retention.get('originals', [])} if retention else {}
    board_rows = []
    for b in by_key.values():
        screenshot = PAPER / 'screenshots' / (b['key'] + '.jpg')
        jsx = PAPER / 'exports' / (b['key'] + '.jsx')
        history = [c for c in captures if c.get('boardKey') == b['key'] and c.get('key') == b['key']]
        all_history = [c for c in captures if c.get('boardKey') == b['key']]
        board_rows.append({
            'key': b['key'], 'file_id': runtime['fileId'], 'page_id': b['pageId'],
            'board_id': b['id'], 'name': b['name'], 'width': b['width'],
            'theme': b.get('theme'), 'page_url': f"https://app.paper.design/file/{runtime['fileId']}/{b['pageId']}",
            'step_ids': b['steps'], 'screenshot': file_receipt(screenshot),
            'jsx': file_receipt(jsx), 'latest_writer_capture': history[-1] if history else None,
            'latest_scoped_capture': all_history[-1] if all_history else None,
            'writer_status': b.get('writer_status', 'BASE_CANDIDATE_OR_IN_PROGRESS; see pending-work record'),
            'qualification': 'NATIVE_DESIGN_ONLY; runtime and reference approval are separate',
        })
    save('native-board-index.json', {
        'schema': 'f02.native-board-index.v1', 'generated_at': now,
        'source_checkpoint': str(runtime_path.relative_to(ROOT)), 'checkpoint_sha256': hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
        'operation_count': len(runtime['operations']),
        'unresolved_operations': [o['id'] for o in runtime['operations'] if (o.get('state') or o.get('response', {}).get('state')) != 'APPLIED_RESPONSE_OBSERVED'],
        'boards': board_rows,
        'boundary': 'IDs derive from actual write responses. Latest capture hashes bind local bytes; final live presence and immutable review freeze are separate receipts.'
    })
    jsx_cache = {}
    for b in board_rows:
        p = PAPER / 'exports' / (b['key'] + '.jsx')
        jsx_cache[b['key']] = p.read_text() if p.exists() else ''

    role_map = read(PAPER / 'role-evidence-input-map.json')
    issues = []

    def bind(e):
        e = copy.deepcopy(e)
        b = by_key.get(e['board_key'])
        if b is None:
            e['binding_status'] = 'NATIVE_BOARD_PENDING'
            issues.append({'board': e['board_key'], 'reason': 'board absent'})
            return e
        e['native_board_id'] = b['id']
        e['native_page_id'] = b['pageId']
        e['native_step_ids'] = {k: b['steps'].get(k) for k in e.get('step_keys', [])}
        missing = [k for k, v in e['native_step_ids'].items() if v is None]
        not_exported = [k for k, v in e['native_step_ids'].items() if v and f'id="{v}"' not in jsx_cache[b['key']]]
        e['binding_status'] = ('NATIVE_STEP_PENDING' if missing else 'FINAL_EXPORT_PENDING' if not_exported else 'ACTUAL_IDS_PRESENT_IN_EXPORT')
        e['unbound_steps'] = missing
        e['steps_not_in_current_export'] = not_exported
        if missing or not_exported:
            issues.append({'board': b['key'], 'missing': missing, 'not_in_export': not_exported})
        e['qualification'] = 'Design evidence binding only; no runtime or RIG approval'
        return e

    roles = copy.deepcopy(role_map['roles'])
    for role in roles:
        for variant in role.get('variants', []):
            variant['evidence'] = [bind(e) for e in variant.get('evidence', [])]
        statuses = [e['binding_status'] for v in role.get('variants', []) for e in v.get('evidence', [])]
        role['native_projection_status'] = ('RETAINED_UNQUALIFIED' if role['role'] in role_map['summary']['retained_unqualified_roles'] else 'BOUND_TO_OBSERVED_CANDIDATE_IDS' if statuses and all(s == 'ACTUAL_IDS_PRESENT_IN_EXPORT' for s in statuses) else 'NATIVE_BINDINGS_IN_PROGRESS')
    cross = copy.deepcopy(role_map['cross_cutting_evidence'])
    for c in cross:
        c['refs'] = [bind(e) for e in c.get('refs', [])]
    save('native-role-bindings.json', {
        'schema': 'f02.native-role-bindings.v1', 'generated_at': now,
        'input_map_sha256': hashlib.sha256((PAPER / 'role-evidence-input-map.json').read_bytes()).hexdigest(),
        'roles': roles, 'cross_cutting_evidence': cross, 'unresolved_bindings': issues,
        'not_proved': role_map['not_proved_by_native_design'],
        'summary': {'contract_roles': len(roles), 'roles_with_new_inputs': 17, 'retained_unqualified_roles': role_map['summary']['retained_unqualified_roles'], 'unresolved_binding_count': len(issues)}
    })

    # General document/archetype predecessors gain shared-anatomy companions only.
    # Their domain composition and approval status are not replaced by this map.
    general = {
        '5FCS-2': ['readme', 'builder'], '423-1': ['readme'], '42T-0': ['readme'], '23T-0': ['readme'],
        '5FE2-2': ['foundations', 'metrics', 'controls-variants', 'states-matrix', 'fault-compositions'],
        '5FGO-2': ['foundations', 'metrics-light', 'controls-variants', 'states-matrix', 'fault-compositions'],
        '5FJA-2': ['macro-dark-en-390', 'company-eps-overlay-320'],
        '5FLR-2': ['macro-light-zh-390', 'macro-zh-evidence-return-390'],
        '30G-0': ['macro-dark-en-390', 'company-eps-overlay-320'],
        '336-0': ['macro-light-zh-390', 'macro-zh-evidence-return-390'],
        '5FO8-2': ['builder'], '3QI-0': ['builder'],
        '5FV9-2': ['readme', 'builder'], '5FY3-2': ['readme', 'builder'],
        '3RX-0': ['readme', 'builder'], '3UP-0': ['readme', 'builder'],
        '3XJ-1': ['foundations'],
        '2S4-0': ['states-matrix', 'fault-compositions'], '2UE-0': ['states-matrix', 'fault-compositions'],
        '2WO-0': ['foundations', 'builder'], '2YK-0': ['foundations', 'builder'],
        '5FPP-2': ['grammar', 'controls-variants', 'fault-compositions', 'macro-dark'],
        '5FSH-2': ['grammar', 'controls-variants', 'fault-compositions', 'macro-light'],
        '35W-0': ['grammar', 'controls-variants', 'fault-compositions', 'macro-dark'],
        '39G-0': ['grammar', 'controls-variants', 'fault-compositions', 'macro-light'],
    }
    component_keys = {}
    for role in roles:
        keys = sorted({e['board_key'] for v in role.get('variants', []) for e in v.get('evidence', [])})
        for pred in role.get('predecessors', []):
            component_keys.setdefault(pred['board_id'], set()).update(keys)
    ledger = read(ROOT / 'paper-retention-ledger.json')
    predecessors = []
    for old in ledger['rows']:
        retained = old['disposition'] == 'RETAIN'
        keys = [] if retained else sorted(set(general.get(old['board_id'], [])) | component_keys.get(old['board_id'], set()))
        assert retained or keys, f"Unmapped improved predecessor: {old['board_id']}"
        targets = []
        for key in keys:
            b = by_key.get(key)
            targets.append({'board_key': key, 'file_id': runtime['fileId'],
                            'page_id': b['pageId'] if b else None, 'board_id': b['id'] if b else None,
                            'status': 'OBSERVED_CANDIDATE_COMPANION' if b else 'PENDING'})
        observed_old = retained_by_id.get((old['file_id'], old['board_id']))
        live_receipt = {'path': 'paper/native-final-retention.json',
                        'sha256': hashlib.sha256(retention_path.read_bytes()).hexdigest(),
                        'observed_at': observed_old['observed_at'],
                        'present': observed_old['present'],
                        'location_matches': observed_old['location_matches'],
                        'name_matches': observed_old['name_matches'],
                        'scope': 'Identity, location and name readback; not original descendant visual audit or approval'} if observed_old else 'Live retention readback pending for this original'
        predecessors.append({
            'file_id': old['file_id'], 'page_id': old['page_id'], 'board_id': old['board_id'],
            'name': old['name'], 'disposition': old['disposition'], 'original_url': old['url'],
            'original_action': 'RETAIN_IN_PLACE_NO_F02_MUTATION',
            'retained_successor': {'file_id': old['file_id'], 'page_id': old['page_id'], 'board_id': old['board_id']} if retained else None,
            'candidate_companions': targets,
            'scope': 'Unchanged original reference; no new approval inferred' if retained else 'Shared anatomy/contract candidate only; original domain semantics, archetype and authority are retained',
            'live_retention_receipt': live_receipt,
        })
    assert len(predecessors) == 67
    save('native-predecessor-bindings.json', {'schema': 'f02.native-predecessor-bindings.v1', 'generated_at': now,
         'counts': ledger['counts'], 'rows': predecessors,
         'boundary': 'No deletion, relocation, replacement approval or domain requalification is claimed. IMPROVE is candidate intent; originals remain preserved.'})
    lines = ['# Native Paper board index', '', 'Generated from the exclusive writer’s observed IDs. Design evidence only; reference approval and runtime proof remain separate. A full capture pair records observed bytes, not completion of pending native repairs or reference acceptance.', '',
             '| Board | Actual ID | Page | Width | Capture / editable export |', '| --- | --- | --- | --- | --- |']
    for b in board_rows:
        artifacts = f"[JPEG](screenshots/{b['key']}.jpg) · [JSX](exports/{b['key']}.jsx)" if b['screenshot'] and b['jsx'] else 'Final capture pending'
        scoped = b.get('latest_scoped_capture')
        if not (b['screenshot'] and b['jsx']) and scoped:
            shot = scoped['screenshot'].removeprefix('f02/paper/')
            export = scoped['jsx'].removeprefix('f02/paper/')
            artifacts += f"; [{scoped['capture_state']} JPEG]({shot}) · [partial JSX]({export})"
        lines.append(f"| {b['key']} | `{b['board_id']}` | [{b['page_id']}]({b['page_url']}) | {b['width']} | {artifacts} |")
    lines += ['', 'The 21-role source-to-native projection is in `native-role-bindings.json`; its unresolved count is explicit. The 67 retained-original/candidate-companion mapping is in `native-predecessor-bindings.json`, with the latest live identity/location receipt where observed. Both distinguish actual native IDs from still-unqualified behavior and domain roles. See `NATIVE_PENDING_WORK.md` for unapplied repairs and absent boards.', '']
    (PAPER / 'NATIVE_BOARD_INDEX.md').write_text('\n'.join(lines))
    print(json.dumps({'boards': len(board_rows), 'complete_capture_pairs': sum(bool(b['screenshot'] and b['jsx']) for b in board_rows),
                      'roles': len(roles), 'predecessors': len(predecessors), 'unresolved_bindings': len(issues)}))


if __name__ == '__main__':
    main()
