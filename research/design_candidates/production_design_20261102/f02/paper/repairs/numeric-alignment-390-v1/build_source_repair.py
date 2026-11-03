#!/usr/bin/env python3
"""Prepare local-only numeric-frame repairs from retained JSX and source inputs."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent.parent
HELPER = HERE.parent / 'build_numeric_alignment_native_patch.py'
module_spec = importlib.util.spec_from_file_location('f02_retained_alignment_parser', HELPER)
parser = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(parser)

FILE_ID = '01M312VSDSZFVT45674GDVJVZN'
MOBILE = HERE.parent / 'fixture-coherence-v1/effective-spaced/mobile-state-boards.json'
SUPPLEMENT = HERE.parent / 'fixture-coherence-v1/effective-spaced/supplemental-boards.json'
PROGRESS = PAPER / 'writer-continuation-progress.json'
NATIVE_STYLE = dict(parser.NATIVE_STYLE)
CSS_STYLE = dict(parser.CSS_STYLE)
NATIVE = {
    'macro-dark-en-390': 'macro-dark-en-390.jsx',
    'macro-light-zh-390': 'macro-light-zh-390--comparison.jsx',
}
PENDING = ['macro-docked-1280', 'width-768-overlay', 'width-1024-overlay', 'width-1600-docked']


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def numeric_source_cells(step, phone):
    root = parser.Parser(step['html']).roots[0]
    header = step['key'] == 'table'
    row = root['children'][0] if header else root
    columns = [1, 2, 3] if header or not phone else [2, 3, 4]
    assert len(row['children']) == (5 if header or not phone else 6)
    cells = [row['children'][i] for i in columns]
    widths = [88, 96, 130] if phone else None
    if widths:
        assert [c['style']['width'] for c in cells] == [f'{n}px' for n in widths]
    for cell in cells:
        assert not cell['children']
        for prop in ['display', 'flex-direction', 'align-items', 'justify-content']:
            assert prop not in cell['style'], (step['key'], prop)
    return root, row, columns, cells, header


def source_override(packet_path, packet_sha, board, step, phone, native_ids=None):
    root, row, columns, cells, header = numeric_source_cells(step, phone)
    # Replace only the exact style attribute bytes of selected numeric cells.
    # All remaining HTML, text, attributes and controls keep their original bytes.
    nodes = [n for n in parser.walk(root) if n['tag'] == 'div']
    openings = list(re.finditer(r'<div\b[^>]*>', step['html']))
    assert len(nodes) == len(openings)
    positions = {id(n): m for n, m in zip(nodes, openings)}
    edits = []
    changes = []
    for column, cell in zip(columns, cells):
        opening = positions[id(cell)]
        match = re.search(r'\bstyle="([^"]*)"', opening.group(0))
        assert match
        original_style = match.group(1)
        delta = {k: v for k, v in CSS_STYLE.items() if cell['style'].get(k) != v}
        replacement_style = original_style + ('' if original_style.rstrip().endswith(';') else ';')
        replacement_style += ''.join(f'{k}: {v};' for k, v in delta.items())
        start = opening.start() + match.start(1)
        end = opening.start() + match.end(1)
        edits.append((start, end, replacement_style))
        changes.append({
            'input_element_path': f'0.0.{column}' if header else f'0.{column}',
            'column_role': ['rate', 'delta_pp', 'coverage'][len(changes)],
            'expected_visible_text': parser.all_text(cell),
            'expected_current_style': cell['style'],
            'style_delta': delta,
            'native_frame_id': native_ids.get(column) if native_ids else None,
        })
    replacement = step['html']
    for start, end, value in sorted(edits, reverse=True):
        replacement = replacement[:start] + value + replacement[end:]
    after = parser.Parser(replacement).roots[0]
    after_nodes = list(parser.walk(after))
    before_nodes = list(parser.walk(root))
    assert len(after_nodes) == len(before_nodes)
    selected = {id(n) for n in cells}
    for before, changed in zip(before_nodes, after_nodes):
        assert before['tag'] == changed['tag'] and before['text'] == changed['text']
        assert len(before['children']) == len(changed['children'])
        if id(before) in selected:
            assert {k: v for k, v in before['attrs'].items() if k != 'style'} == {k: v for k, v in changed['attrs'].items() if k != 'style'}
            assert changed['style'] == {**before['style'], **CSS_STYLE}
        else:
            assert before['attrs'] == changed['attrs'] and before['style'] == changed['style']
    return {
        'source_packet': str(packet_path),
        'source_packet_sha256': packet_sha,
        'board_key': board['key'],
        'step_key': step['key'],
        'source_step_html_sha256': sha(step['html']),
        'accepted_before_overlay_html_sha256': [sha(step['html'])],
        'replacement_html_sha256': sha(replacement),
        'cell_overrides': changes,
        'replacement_html': replacement,
    }


def main():
    mobile_bytes, supplement_bytes, progress_bytes = MOBILE.read_bytes(), SUPPLEMENT.read_bytes(), PROGRESS.read_bytes()
    assert sha(mobile_bytes) == '276572f02660d9b6be25473bdf039b28aea10ad31a1d0813bec6812caf804399'
    assert sha(supplement_bytes) == 'e65ecfcec783c752651634541d6f9917857e2da42e4686bdae0535cd089aaa2e'
    mobile, supplement, progress = map(json.loads, [mobile_bytes, supplement_bytes, progress_bytes])
    assert progress['fileId'] == FILE_ID
    source_boards = {b['key']: b for b in mobile['boards'] + supplement['boards']}
    actual_boards = {b['key']: b for b in progress['boards']}
    operations = [op for op in progress['operations'] if any(op.get('id', '').startswith(f'f02-c2-{key}-') for key in NATIVE)]
    receipts = parser.created_receipts({'operations': operations})
    evidence_hashes = {str(MOBILE): sha(mobile_bytes), str(SUPPLEMENT): sha(supplement_bytes), str(PROGRESS): sha(progress_bytes), str(HELPER): sha(HELPER.read_bytes())}
    bindings, batches, mobile_overrides, summaries = [], [], [], []
    untouched_controls = []

    for key, filename in NATIVE.items():
        board, actual = source_boards[key], actual_boards[key]
        export = PAPER / 'exports' / filename
        export_bytes = export.read_bytes()
        evidence_hashes[str(export)] = sha(export_bytes)
        root, index = parser.parse_jsx(export_bytes.decode())
        assert root['attrs']['id'] == actual['id']
        assert actual['pageId'] == 'p-5-0' and actual['width'] == 390
        step_list = [s for s in board['steps'] if s['key'] == 'table' or s['key'].startswith('sector-')]
        assert len(step_list) == 11
        board_bindings = []
        for step in step_list:
            source_root, source_row, columns, cells, header = numeric_source_cells(step, True)
            step_root = index[actual['steps'][step['key']]]
            row = step_root['children'][0] if header else step_root
            assert row['style']['width'] == '650px'
            assert row['style']['height'] == ('36px' if header else '56px')
            assert len(row['children']) == len(source_row['children'])
            assert [parser.all_text(n) for n in row['children']] == [parser.all_text(n) for n in source_row['children']]
            native_ids = {}
            for column, cell in zip(columns, cells):
                frame = row['children'][column]
                frame_id = frame['attrs']['id']
                assert receipts[frame_id]['component'] == 'Frame'
                assert len(frame['children']) == 1 and not parser.normalized(frame['text'])
                text_node = frame['children'][0]
                text_id = text_node['attrs']['id']
                assert receipts[text_id]['component'] == 'Text' and not text_node['children']
                assert receipts[frame_id]['operation_id'] == receipts[text_id]['operation_id'] == receipts[step_root['attrs']['id']]['operation_id']
                assert frame['style']['width'] == cell['style']['width']
                assert parser.all_text(frame) == parser.all_text(cell)
                assert all(prop not in frame['style'] for prop in ['display', 'flexDirection', 'alignItems', 'justifyContent'])
                if cell['style'].get('text-align') == 'right':
                    assert frame['style'].get('textAlign') == 'right'
                else:
                    assert 'textAlign' not in frame['style']
                for css_prop, native_prop in [('padding-right', 'paddingRight'), ('padding-left', 'paddingLeft')]:
                    assert frame['style'].get(native_prop) == cell['style'].get(css_prop)
                native_ids[column] = frame_id
                binding = {
                    'board_key': key, 'board_id': actual['id'], 'page_id': actual['pageId'],
                    'step_key': step['key'], 'step_root_node_id': step_root['attrs']['id'],
                    'row_node_id': row['attrs']['id'], 'row_role': 'header' if header else 'body',
                    'row_identity': parser.all_text(row['children'][0]),
                    'column_index_zero_based': column,
                    'column_role': ['rate', 'delta_pp', 'coverage'][columns.index(column)],
                    'node_id': frame_id, 'native_component': 'Frame',
                    'text_node_id_unchanged': text_id,
                    'exact_visible_text_unchanged': parser.all_text(frame),
                    'expected_current_frame_style': frame['style'],
                    'expected_current_text_style_unchanged': text_node['style'],
                    'expected_absent_layout_properties': ['display', 'flexDirection', 'alignItems', 'justifyContent'],
                    'desired_styles': NATIVE_STYLE,
                    'changed_properties': {p: {'from': frame['style'].get(p), 'to': v, 'from_absent': p not in frame['style']} for p, v in NATIVE_STYLE.items() if frame['style'].get(p) != v},
                    'binding_evidence': {'kind': 'retained_JSX_and_APPLIED_createdNodes', 'export': str(export), 'export_sha256': sha(export_bytes), 'operation_id': receipts[frame_id]['operation_id'], 'frame_component': 'Frame', 'text_component': 'Text'},
                }
                bindings.append(binding)
                board_bindings.append(binding)
            for column, cell in enumerate(row['children']):
                if column not in columns:
                    untouched_controls.append({'board_key': key, 'step_key': step['key'], 'node_id': cell['attrs']['id'], 'text': parser.all_text(cell)})
            mobile_overrides.append(source_override(MOBILE, sha(mobile_bytes), board, step, True, native_ids))
        assert len(board_bindings) == 33
        batches.append({
            'board_key': key, 'board_id': actual['id'], 'page_id': actual['pageId'],
            'tool': 'update_styles',
            'arguments': {'fileId': FILE_ID, 'updates': [{'nodeIds': [b['node_id']], 'styles': NATIVE_STYLE} for b in board_bindings]},
            'numeric_frames': 33,
            'apply_guard': 'Preparation only. Sole writer must resolve applicable effect uncertainty, fresh-read exact retained Frame/Text bindings and current styles, and supply a fresh direct-carrier snapshot. No replay or inferred replacement IDs.',
            'post_apply_check': 'Same-carrier JSX and screenshot readback must establish end alignment and unchanged text, controls, widths, padding, row identities and geometry. No tool acknowledgment alone is rendered proof.',
        })
        summaries.append({'board_key': key, 'board_id': actual['id'], 'export': str(export), 'export_sha256': sha(export_bytes), 'numeric_frames': 33, 'header_frames': 3, 'body_frames': 30, 'source_steps': 11})

    pending_overrides = []
    for key in PENDING:
        board = source_boards[key]
        packet, packet_bytes = (MOBILE, mobile_bytes) if key == 'macro-docked-1280' else (SUPPLEMENT, supplement_bytes)
        assert key not in actual_boards, (key, 'No longer pending in retained writer progress; reconcile before producing unbound source overrides.')
        steps = [s for s in board['steps'] if s['key'] == 'table' or s['key'].startswith('sector-')]
        assert len(steps) == 11
        for step in steps:
            pending_overrides.append(source_override(packet, sha(packet_bytes), board, step, False))
    returned = source_boards['macro-zh-evidence-return-390']
    return_step = next(s for s in returned['steps'] if s['key'] == 'returned-selected-row')
    _, _, _, return_cells, _ = numeric_source_cells(return_step, True)
    related_return_flag = {
        'board_key': returned['key'], 'step_key': return_step['key'],
        'source_packet': str(SUPPLEMENT), 'source_packet_sha256': sha(supplement_bytes),
        'source_step_html_sha256': sha(return_step['html']),
        'affected_column_roles': ['rate', 'delta_pp', 'coverage'],
        'expected_visible_values': [parser.all_text(c) for c in return_cells],
        'finding': 'The same authored numeric-cell structure is present in this pending selected-return row. Flagged for the owner; not included in the requested two-board native patch or four-width source override.',
    }
    assert len(bindings) == 66 and len({b['node_id'] for b in bindings}) == 66
    assert len({b['text_node_id_unchanged'] for b in bindings}) == 66
    assert len(mobile_overrides) == 22 and len(pending_overrides) == 44
    assert len(untouched_controls) == 64
    assert not ({b['node_id'] for b in bindings} & {c['node_id'] for c in untouched_controls})
    for path, expected in evidence_hashes.items():
        assert sha(Path(path).read_bytes()) == expected, ('input changed during preparation', path)

    patch = {
        'schema': 'f02.paper.numeric-alignment-390-native-patch.v1',
        'status': 'PREPARED_FROM_RETAINED_EXPORTS_NOT_APPLIED_NOT_LIVE_VALIDATED',
        'target_file_id': FILE_ID,
        'scope': 'Only rate, delta and coverage numeric frames and their headers in the two owned 390px Macro boards.',
        'observed_source_issue': 'The retained actual JSX numeric frames have no explicit flex-column/end layout; coverage also lacks textAlign:right. This confirms missing frame-end layout, not a new rendered observation.',
        'repair': 'Add flex column / end cross-axis alignment / centered main axis / right text alignment to numeric Frames only. Keep Text nodes, dimensions, padding, labels, values and source controls unchanged.',
        'counts': {'boards': 2, 'frames': 66, 'header_frames': 6, 'body_frames': 60, 'source_steps': 22, 'preserved_non_numeric_cells': 64},
        'evidence_hashes': evidence_hashes,
        'batches': batches, 'bindings': bindings,
        'preserved_non_numeric_cells': untouched_controls,
        'unresolved_operation': {'operation_id': 'f02-c2-macro-light-zh-390-chart-footer-20261103-01', 'target': '7J4-0', 'status': 'UNRESOLVED', 'effect_on_this_packet': 'This preparation supplies no reconciliation or dispatch authority. Keep applicable target writes paused pending the existing owner gate.'},
        'ambiguous_targets': [], 'paper_calls': 0, 'browser_calls': 0,
        'native_mutations_performed': False, 'rendered_fix_verified': False,
    }
    patch_path = HERE / 'native-patch.v1.json'
    dump(patch_path, patch)
    common = {
        'status': 'PREPARED_SOURCE_DELTA_ONLY_NOT_APPLIED',
        'instruction': 'Compose only against the exact before HTML hash. Change style attributes on the listed numeric source cells only. Preserve original packets and applied receipts. Never replay an applied construction step to obtain this style repair.',
        'style_delta': CSS_STYLE,
        'precedence': 'Apply after fixture-coherence-v1/effective-spaced input. No Company, Options, chart, footer, evidence identity or clock overlay is superseded.',
        'paper_calls': 0, 'browser_calls': 0,
    }
    mobile_path = HERE / 'source-overrides.v1.json'
    dump(mobile_path, {'schema': 'f02.paper.numeric-alignment-390-source-overrides.v1', **common, 'native_patch_sha256': sha(patch_path.read_bytes()), 'overrides': mobile_overrides})
    pending_path = HERE / 'pending-width-source-overrides.v1.json'
    dump(pending_path, {
        'schema': 'f02.paper.numeric-alignment-pending-width-source-overrides.v1', **common,
        'scope': 'Unbuilt 1280 dock plus 768, 1024 and 1600 width studies; 44 source steps / 132 numeric cells. No native IDs or live state are invented.',
        'retained_progress_sha256': sha(progress_bytes),
        'native_binding_status': 'NOT_BOUND; boards absent from retained progress, no live read performed',
        'clone_guard_note': 'Compose corresponding 1280 and 1600 source overrides before a clone build. The old supplemental-wide-clone.json input HTML hashes remain historical and must be refreshed against the effective aligned inputs; this file does not assert a newly qualified clone plan.',
        'overrides': pending_overrides,
        'related_pending_return_row_flag': related_return_flag,
    })
    validation = {
        'schema': 'f02.paper.numeric-alignment-390-source-validation.v1',
        'status': 'SOURCE_BINDINGS_AND_STYLE_ONLY_DIFF_PASS_NOT_LIVE_VALIDATED',
        'files': {p.name: sha(p.read_bytes()) for p in [patch_path, mobile_path, pending_path]},
        'boards': summaries,
        'checks': {
            '66_unique_frame_and_text_bindings': True,
            'all_native_roles_from_APPLIED_createdNodes': True,
            'actual_export_rows_match_source_values_and_widths': True,
            'all_66_frames_lack_explicit_end_layout': True,
            'all_text_nodes_and_64_non_numeric_cells_unchanged': True,
            'source_deltas_only_selected_style_attribute_bytes': True,
            'all_existing_padding_widths_row_heights_colors_fonts_and_text_preserved': True,
            '44_pending_width_steps_cover_132_numeric_cells': True,
            'all_inputs_and_exports_unchanged': True,
        },
        'related_pending_return_row_flag': related_return_flag,
        'mismatches': [], 'paper_calls': 0, 'browser_calls': 0, 'applied': False,
    }
    validation_path = HERE / 'validation.json'
    dump(validation_path, validation)
    print(json.dumps({'files': {str(p): sha(p.read_bytes()) for p in [patch_path, mobile_path, pending_path, validation_path]}, 'counts': patch['counts'], 'pending_width_steps': 44, 'pending_width_cells': 132, 'mismatches': []}, indent=2))


if __name__ == '__main__':
    main()
