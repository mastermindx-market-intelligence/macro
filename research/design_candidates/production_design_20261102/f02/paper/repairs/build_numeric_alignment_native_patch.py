#!/usr/bin/env python3
"""Bind a local, unapplied numeric-frame repair to actual six-board JSX exports.

This script never connects to Paper and never changes exports or applied inputs.
It fails closed on an ambiguous row, column, ID, frame role, or current style.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
F02 = PAPER.parent
FILE_ID = '01M312VSDSZFVT45674GDVJVZN'
PACKET = PAPER / 'consumer-inputs/consumer-boards.json'
PROGRESS = PAPER / 'native-progress.json'
NATIVE_STYLE = {
    'display': 'flex',
    'flexDirection': 'column',
    'alignItems': 'end',
    'justifyContent': 'center',
    'textAlign': 'right',
}
CSS_STYLE = {
    'display': 'flex',
    'flex-direction': 'column',
    'align-items': 'end',
    'justify-content': 'center',
    'text-align': 'right',
}
SPEC = {
    'macro': {
        'header': 'table-header',
        'body': [f'sector-{n}' for n in range(1, 11)],
        'columns': ['Sector', 'Above 50D', 'Change · pp', 'Covered / eligible', 'Source'],
        'numeric': [1, 2, 3],
        'widths': [254, 126, 130, 164, 150],
        'row_width': 824,
    },
    'company': {
        'header': 'statement-header',
        'body': [f'statement-row-{n}' for n in range(1, 10)],
        'columns': ['Reported metric', 'FY 2022', 'FY 2023', 'FY 2024', 'FY 2025', 'FY 2026', 'FY26 / FY25 change', 'Source'],
        'numeric': [1, 2, 3, 4, 5, 6],
        'widths': [250, 125, 125, 125, 125, 125, 165, 128],
        'row_width': 1168,
    },
    'options': {
        'header': 'tape-header',
        'body': [f'print-{n:02}' for n in range(1, 13)],
        'columns': ['Instrument', 'Time · ET', 'Expiry', 'Type', 'Strike · USD', 'Est. side', 'Premium · USD', 'Contracts', 'DTE', 'Moneyness', 'Flags', 'Source'],
        'numeric': [4, 6, 7, 8],
        'widths': [93, 89, 119, 70, 104, 103, 129, 103, 55, 109, 97, 97],
        'row_width': 1168,
    },
}


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def normalized(value):
    return re.sub(r'\s+', ' ', html.unescape(value)).strip()


def css(value):
    return {k.strip(): v.strip() for part in value.split(';') if ':' in part for k, v in [part.split(':', 1)]}


class Parser(HTMLParser):
    def __init__(self, source, styles=None):
        super().__init__(convert_charrefs=True)
        self.roots = []
        self.stack = []
        self.styles = styles or {}
        self.feed(source)
        assert not self.stack, 'unclosed markup'

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = {'tag': tag, 'attrs': attrs, 'text': '', 'children': []}
        node['style'] = self.styles.get(attrs.get('data-jsx-style-id'), css(attrs.get('style', '')))
        node['parent_id'] = self.stack[-1]['attrs'].get('id') if self.stack else None
        (self.stack[-1]['children'] if self.stack else self.roots).append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.stack.pop()

    def handle_endtag(self, tag):
        assert self.stack and self.stack[-1]['tag'] == tag, ('unmatched tag', tag)
        self.stack.pop()

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]['text'] += data


def walk(node):
    yield node
    for child in node['children']:
        yield from walk(child)


def all_text(node):
    return normalized(' '.join(n['text'] for n in walk(node)))


def parse_js_style(body):
    pattern = re.compile(r'''([A-Za-z_$][\w$]*)\s*:\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|true|false|null)''')
    result = {}
    end = 0
    for match in pattern.finditer(body):
        assert not body[end:match.start()].strip(' ,\n\t\r'), ('unsupported JSX style', body[end:match.start()])
        key, value = match.groups()
        assert key not in result
        result[key] = {'true': True, 'false': False, 'null': None}.get(value) if value in ['true', 'false', 'null'] else ast.literal_eval(value)
        end = match.end()
    assert not body[end:].strip(' ,\n\t\r'), ('unsupported trailing JSX style', body[end:])
    return result


def parse_jsx(source):
    styles = {}

    def replace(match):
        key = str(len(styles))
        styles[key] = parse_js_style(match.group(1))
        return f'data-jsx-style-id="{key}"'

    clean = re.sub(r'style=\{\{(.*?)\}\}', replace, source, flags=re.S)
    parser = Parser(clean, styles)
    assert len(parser.roots) == 1
    nodes = list(walk(parser.roots[0]))
    index = {n['attrs']['id']: n for n in nodes if 'id' in n['attrs']}
    assert len(index) == sum('id' in n['attrs'] for n in nodes), 'duplicate actual ID'
    return parser.roots[0], index


def serialized(node):
    attrs = ''.join(f' {k}="{html.escape(str(v), quote=True)}"' for k, v in node['attrs'].items())
    return f'<{node["tag"]}{attrs}>' + html.escape(node['text'], quote=False) + ''.join(serialized(c) for c in node['children']) + f'</{node["tag"]}>'


def created_receipts(progress):
    result = {}
    for operation in progress['operations']:
        if operation.get('tool') != 'write_html' or operation.get('state') != 'APPLIED_RESPONSE_OBSERVED':
            continue
        for block in operation.get('result', {}).get('content', []):
            if block.get('type') != 'text':
                continue
            try:
                content = json.loads(block['text'])
            except (ValueError, TypeError):
                continue
            for node in content.get('createdNodes', []):
                assert node['id'] not in result
                result[node['id']] = {'operation_id': operation['id'], 'component': node['component'], 'name': node['name']}
    return result


def main():
    packet_bytes = PACKET.read_bytes()
    progress_bytes = PROGRESS.read_bytes()
    packet = json.loads(packet_bytes)
    progress = json.loads(progress_bytes)
    assert progress['fileId'] == FILE_ID
    source_boards = {b['key']: b for b in packet['boards']}
    actual_boards = {b['key']: b for b in progress['boards']}
    receipts = created_receipts(progress)
    bindings = []
    board_batches = []
    source_overrides = []
    source_hashes = {'consumer_packet': sha(packet_bytes), 'native_progress_at_binding': sha(progress_bytes), 'system_contract': sha((F02 / 'SYSTEM_CONTRACT.md').read_bytes())}
    untouched_hashes = {str(PACKET): sha(packet_bytes)}
    expected_counts = {}
    dark_index = {}
    validation_boards = []

    for domain, spec in SPEC.items():
        assert sum(spec['widths']) == spec['row_width']
        for theme in ['dark', 'light']:
            key = f'{domain}-{theme}'
            src = source_boards[key]
            actual = actual_boards[key]
            individual_path = PAPER / 'consumer-inputs' / f'{key}.json'
            assert json.loads(individual_path.read_text()) == src
            untouched_hashes[str(individual_path)] = sha(individual_path.read_bytes())
            export_path = PAPER / 'exports' / f'{key}.jsx'
            exported = export_path.read_text()
            untouched_hashes[str(export_path)] = sha(exported)
            root, index = parse_jsx(exported)
            assert root['attrs']['id'] == actual['id']
            assert actual['pageId'] == 'p-6-0'
            if theme == 'dark':
                dark_index[domain] = index
            else:
                assert actual['clone_source'] == actual_boards[f'{domain}-dark']['id']
            src_steps = {s['key']: s for s in src['steps']}
            steps = [spec['header'], *spec['body']]
            board_binding = []
            unchanged_cells = []

            for step_key in steps:
                source_step = src_steps[step_key]
                source_tree = Parser(source_step['html'])
                assert len(source_tree.roots) == 1
                source_row = source_tree.roots[0]
                row_id = actual['steps'][step_key]
                row = index[row_id]
                assert row['parent_id'] == actual['steps'][source_step['parent']]
                assert row['style']['width'] == f'{spec["row_width"]}px'
                assert row['style']['display'] == 'flex'
                assert row['style']['alignItems'] == 'center'
                assert len(row['children']) == len(source_row['children']) == len(spec['columns'])
                header = step_key == spec['header']
                if header:
                    assert [all_text(c) for c in row['children']] == spec['columns']
                    assert [all_text(c) for c in source_row['children']] == spec['columns']
                source_changed = copy.deepcopy(source_row)
                step_changes = []

                for col, (frame, source_cell) in enumerate(zip(row['children'], source_row['children'])):
                    expected_width = f'{spec["widths"][col]}px'
                    assert frame['style']['width'] == source_cell['style']['width'] == expected_width
                    assert all_text(frame) == all_text(source_cell), (key, step_key, col, all_text(frame), all_text(source_cell))
                    if col not in spec['numeric']:
                        unchanged_cells.append(frame['attrs']['id'])
                        continue
                    node_id = frame['attrs']['id']
                    assert frame['tag'] == 'div' and len(frame['children']) == 1
                    text_node = frame['children'][0]
                    assert not text_node['children'] and not normalized(frame['text'])
                    assert text_node['style']['width'] == 'max-content'
                    assert text_node['style']['fontFeatureSettings'] == '"tnum"'
                    assert text_node['style']['fontSize'] == ('11px' if header else '13px')
                    assert frame['style']['paddingInline'] == '10px'
                    assert frame['style']['flexShrink'] == '0'
                    assert frame['style']['boxSizing'] == 'border-box'
                    # Fail closed if already repaired or otherwise changed since this export.
                    for prop in ['display', 'flexDirection', 'alignItems', 'justifyContent']:
                        assert prop not in frame['style'], (key, node_id, prop, 'unexpected existing layout')
                    option_header = domain == 'options' and header
                    if option_header:
                        assert source_cell['style']['text-align'] == 'left'
                        assert 'textAlign' not in frame['style'] and 'textAlign' not in text_node['style']
                    else:
                        assert source_cell['style']['text-align'] == 'right'
                        assert frame['style']['textAlign'] == text_node['style']['textAlign'] == 'right'

                    if theme == 'dark':
                        receipt = receipts[node_id]
                        assert receipt['component'] == 'Frame'
                        assert receipts[text_node['attrs']['id']]['component'] == 'Text'
                        assert receipt['operation_id'] == receipts[row_id]['operation_id']
                        role_evidence = {'kind': 'observed_createdNodes', **receipt, 'text_component': 'Text'}
                    else:
                        dark_row_id = actual_boards[f'{domain}-dark']['steps'][step_key]
                        dark_frame = dark_index[domain][dark_row_id]['children'][col]
                        source_id = dark_frame['attrs']['id']
                        source_text_id = dark_frame['children'][0]['attrs']['id']
                        assert actual['descendantIdMap'][source_id] == node_id
                        assert actual['descendantIdMap'][source_text_id] == text_node['attrs']['id']
                        assert receipts[source_id]['component'] == 'Frame'
                        assert receipts[source_text_id]['component'] == 'Text'
                        role_evidence = {'kind': 'observed_descendantIdMap_and_target_JSX', 'source_node_id': source_id, 'source_text_node_id': source_text_id, 'source_component': 'Frame', 'source_operation_id': receipts[source_id]['operation_id']}

                    change = {
                        'board_key': key, 'board_id': actual['id'], 'step_key': step_key,
                        'row_node_id': row_id, 'row_role': 'header' if header else 'body',
                        'row_identity': all_text(row['children'][0]),
                        'column_index_zero_based': col, 'column_name': spec['columns'][col],
                        'node_id': node_id, 'native_component': 'Frame',
                        'text_node_id_unchanged': text_node['attrs']['id'],
                        'exact_visible_text_unchanged': all_text(frame),
                        'expected_current_frame_style': frame['style'],
                        'expected_current_text_style_unchanged': text_node['style'],
                        'expected_absent_layout_properties': ['display', 'flexDirection', 'alignItems', 'justifyContent'],
                        'desired_styles': NATIVE_STYLE,
                        'changed_properties': {p: {'from': frame['style'].get(p), 'to': v, 'from_absent': p not in frame['style']} for p, v in NATIVE_STYLE.items() if frame['style'].get(p) != v},
                        'role_binding_evidence': role_evidence,
                    }
                    bindings.append(change)
                    board_binding.append(change)

                    changed_cell = source_changed['children'][col]
                    old_style = dict(source_cell['style'])
                    new_style = {**old_style, **CSS_STYLE}
                    changed_cell['attrs']['style'] = ''.join(f'{p}:{v};' for p, v in new_style.items())
                    changed_cell['style'] = new_style
                    step_changes.append({
                        'input_element_path': f'0.{col}', 'column_name': spec['columns'][col],
                        'expected_visible_text': all_text(source_cell),
                        'expected_current_style': old_style,
                        'style_delta': {p: {'from': old_style.get(p), 'to': v, 'from_absent': p not in old_style} for p, v in CSS_STYLE.items() if old_style.get(p) != v},
                        'observed_native_frame_id': node_id,
                    })

                replacement_html = serialized(source_changed)
                replacement_tree = Parser(replacement_html).roots[0]
                assert [all_text(c) for c in replacement_tree['children']] == [all_text(c) for c in source_row['children']]
                for col, (before, after) in enumerate(zip(source_row['children'], replacement_tree['children'])):
                    assert before['attrs'].keys() == after['attrs'].keys()
                    for attr in before['attrs']:
                        if attr != 'style' or col not in spec['numeric']:
                            assert before['attrs'][attr] == after['attrs'][attr]
                    assert before['style']['width'] == after['style']['width']
                    assert before['children'] == after['children']
                    if col in spec['numeric']:
                        assert after['style'] == {**before['style'], **CSS_STYLE}
                source_overrides.append({
                    'board_key': key, 'step_key': step_key,
                    'source_step_html_sha256': sha(source_step['html']),
                    'replacement_html_sha256': sha(replacement_html),
                    'cell_overrides': step_changes,
                    'replacement_html': replacement_html,
                })

            expected = len(steps) * len(spec['numeric'])
            assert len(board_binding) == expected
            expected_counts[key] = expected
            updates = [{'nodeIds': [b['node_id']], 'styles': NATIVE_STYLE} for b in board_binding]
            board_batches.append({
                'board_key': key, 'board_id': actual['id'], 'page_id': actual['pageId'],
                'source_export': str(export_path), 'source_export_sha256': sha(exported),
                'numeric_frame_count': expected, 'header_frames': len(spec['numeric']),
                'body_frames': len(spec['body']) * len(spec['numeric']),
                'tool': 'update_styles', 'arguments': {'updates': updates},
                'apply_guard': 'Re-read the named owned board and match the per-node expected styles/identity before applying. A changed or absent node is a stop for that target, not permission to infer a replacement.',
                'post_apply_check': 'Read JSX and screenshot. Confirm frame column/end alignment, invariant widths/padding/values, source fields and all rows; do not mark rendered fix from a tool acknowledgment alone.',
            })
            validation_boards.append({
                'board_key': key, 'actual_board_id': actual['id'], 'rows_including_header': len(steps),
                'numeric_columns': [spec['columns'][n] for n in spec['numeric']],
                'numeric_frame_count': expected, 'all_frame_and_text_roles_bound': True,
                'all_expected_current_styles_match_export': True,
                'unmodified_non_numeric_cell_count': len(unchanged_cells),
                'unmodified_non_numeric_cell_ids': unchanged_cells,
                'source_export_sha256': sha(exported),
            })

    assert len(bindings) == 290 and len(source_overrides) == 68
    assert len({b['node_id'] for b in bindings}) == len(bindings)
    for path, expected_hash in untouched_hashes.items():
        assert sha(Path(path).read_bytes()) == expected_hash, ('source changed during binding', path)

    patch = {
        'schema': 'f02.paper.numeric-alignment-native-patch.v1',
        'status': 'PREPARED_NOT_APPLIED', 'target_file_id': FILE_ID,
        'scope': 'Only numeric header/body cell frames in six owned consumer boards on p-6-0.',
        'rule': {'source': str(F02 / 'SYSTEM_CONTRACT.md'), 'section': '3 / typography table / Table body', 'exact_text': 'Numeric columns align to the end; preserve precision and unit labels'},
        'source_hashes': source_hashes,
        'observed_problem': 'Fixed-width frames contain max-content text nodes. Text alignment on an intrinsic-width child does not place that child at the end of the cell frame. Options numeric headers also entered as left-aligned.',
        'repair': 'Match the already repaired metrics frame anatomy: flex column, end cross-axis alignment, centered main axis; numeric headers inherit right text alignment. Preserve widths, padding, precision, units, field/source identity and chart nodes.',
        'counts': {'boards': 6, 'numeric_frames': 290, 'header_frames': 26, 'body_frames': 264, 'source_steps': 68, 'per_board': expected_counts},
        'batches': board_batches,
        'bindings': bindings,
        'untouched_artifacts_sha256': untouched_hashes,
        'ambiguous_targets': [],
        'native_mutations_performed': False, 'paper_calls': 0, 'browser_calls': 0,
        'rendered_fix_verified': False,
        'execution_note': 'Batches provide updates/nodeIds/styles payloads. Root owns the qualified direct-call envelope, current session guard and native readback. Snapshot hashes are not document revisions.',
    }
    patch_path = HERE / 'numeric-alignment-native-patch.json'
    dump(patch_path, patch)
    override = {
        'schema': 'f02.paper.numeric-alignment-source-override.v1',
        'status': 'PREPARED_NOT_APPLIED',
        'source_packet': str(PACKET), 'source_packet_sha256': sha(packet_bytes),
        'instruction': 'Do not mutate the applied-input evidence. For any explicitly authorized later reconstruction, overlay these exact replacements only after original step hash verification. Native execution uses the separately bound ID patch.',
        'change_scope': 'Four frame-layout declarations and numeric text alignment only; all text, row/column order, widths, padding, data, source and chart content retained.',
        'native_patch_sha256': sha(patch_path.read_bytes()),
        'overrides': source_overrides,
    }
    override_path = HERE / 'numeric-alignment-source-input-override.json'
    dump(override_path, override)
    report = {
        'schema': 'f02.paper.numeric-alignment-verification.v1',
        'status': 'PASS_LOCAL_BINDING_ONLY', 'native_patch_applied': False,
        'native_patch_sha256': sha(patch_path.read_bytes()),
        'source_override_sha256': sha(override_path.read_bytes()),
        'applied_input_packet_unchanged_sha256': sha(PACKET.read_bytes()),
        'boards': validation_boards,
        'numeric_frames': len(bindings), 'source_steps': len(source_overrides),
        'ambiguous_targets': [],
        'evidence': ['SYSTEM_CONTRACT numeric end-alignment rule', 'actual JSX parent/child IDs, widths, text and styles', 'native-progress actual board/step map', 'observed write_html createdNodes frame/text roles', 'light-board observed descendantIdMap with target JSX cross-check'],
        'preservation_checks': ['applied packet and individual inputs hash unchanged', 'export hashes unchanged', 'row/column text and precision unchanged', 'cell widths and padding unchanged', 'non-numeric cells and source column unchanged', 'no SVG/chart node targeted', 'no native text node targeted'],
        'limits': ['Current native state must be re-read after reconnect; local exports are a bounded observation, not a live lock.', 'No screenshot or rendered fit was inspected for this repair.', 'No Paper/browser call or native mutation was performed.', 'Artifact shows intended design alignment; it does not prove interactive sorting or source services.'],
    }
    dump(HERE / 'numeric-alignment-verification.json', report)
    print(json.dumps({'status': report['status'], 'counts': patch['counts'], 'patch_sha256': report['native_patch_sha256'], 'override_sha256': report['source_override_sha256'], 'ambiguous_targets': []}, indent=2))


if __name__ == '__main__':
    main()
