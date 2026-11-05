#!/usr/bin/env python3
"""Prepare bounded directory/source-note groups from actual writer IDs.

No Paper call. Run after all intended boards exist, then give the resulting
packet to the exclusive writer for fresh target checks and incremental edits.
"""
from pathlib import Path
from html import escape
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
PAPER = ROOT / 'paper'
FILE = '01M312VSDSZFVT45674GDVJVZN'
BRANCH = 'design/f02-system-v1-20261102-c2'
BASE = f'https://github.com/mastermindx-market-intelligence/macro/blob/{BRANCH}/research/design_candidates/production_design_20261102/f02/'


def text(value, size=14, weight=400, color='var(--noir-text-secondary)', width=1296):
    return f'<div style="display:flex;font-family:Inter;font-size:{size}px;line-height:{size+7}px;font-weight:{weight};color:{color};width:{width}px;flex-shrink:0;">{escape(value)}</div>'


def link(label, url):
    # Preserve the exact URL visibly even if the native importer drops link behavior.
    return text(label, 14, 600, 'var(--noir-text-primary)') + f'<a href="{escape(url, quote=True)}" style="display:flex;font-family:Inter;font-size:13px;line-height:20px;color:var(--noir-champagne);text-decoration:underline;width:1296px;flex-shrink:0;">{escape(url)}</a>'


def block(title, body):
    return '<div style="display:flex;flex-direction:column;gap:10px;padding:20px 24px;background-color:var(--noir-panel);width:1344px;">' + text(title, 18, 600, 'var(--noir-text-primary)') + body + '</div>'


def main():
    source = WORK / 'f02_writer_runtime.json'
    r = json.loads(source.read_text())
    boards = {b['key']: b for b in r['boards']}
    readme, builder = boards['readme'], boards['builder']
    pages = [
        ('p-3-0', '02 · Foundations', 'Semantic colors, type, spacing, density and existing icon anatomy.'),
        ('p-4-0', '03 · Components', 'Metrics, buttons/tabs/disclosures, exact evidence, read/access/save states and exceptional compositions.'),
        ('p-5-0', '04 · Patterns', 'Chart/table grammar, narrow evidence, responsive widths, localized return paths and density examples.'),
        ('p-6-0', '05 · Reference Screens', 'Macro, Company, Options and public editorial in both themes. These are representative shared-pattern compositions.'),
        ('p-7-0', '06 · Utilities', 'Source ownership, integration sequence, acceptance, performance targets and rollback.'),
    ]
    rows = []
    for page_id, title, purpose in pages:
        scoped = [b for b in boards.values() if b['pageId'] == page_id]
        labels = ' · '.join(f"{b['key']} [{b['id']}]" for b in scoped)
        body = text(purpose) + text(labels, 13) + link('Open the observed page; use the exact board IDs above', f'https://app.paper.design/file/{FILE}/{page_id}')
        rows.append({'key': 'directory-' + page_id, 'parent': 'board', 'html': block(title, body)})
    source_html = block('Source contract and exact review identity',
        link('Current build contract — draft branch navigation', BASE + 'SYSTEM_CONTRACT.md') +
        link('Source/data and fixture authority', BASE + 'SOURCE_AND_DATA_CONTRACT.md') +
        link('Native board/capture index and immutable review references', BASE + 'paper/README.md') +
        link('Independent review record and open gates', BASE + 'paper/reviews/NATIVE_REVIEW_REPORT.md') +
        text('These links navigate the current draft. The source manifests identify immutable reviewed bytes; a mutable Paper URL, snapshot guard or token hash does not establish approval.', 13))
    limit_html = block('Candidate boundary and retained responsibilities',
        text('F02 owns shared anatomy and tokens. F01 owns the joint shell/navigation contract. Domain owners retain their source identities, routes, access rules, verdicts, count partitions, lifecycle transitions and saved-state authority.') +
        text('The repaired native subset is applied and captured. The Chinese comparison board 7IS-0 remains incomplete under its original unresolved chart-footer operation; its separate evidence-return companion does not replace it. Release remains held for terminal reconciliation, full-set review, F01 joint qualification, actual browser keyboard/touch/400% proof, complete consumer/domain integration and formal admitted review.') +
        text('F02 retains the accepted candidate.2 geometry and records clause-specific concurrence with F01 candidate.4. Brain Close is distinct from Stop; conditional focus ownership, the focused Terminal reader exception and the existing shared-component owners remain explicit source contracts, not executed runtime proof.', 13) +
        text('All numerical examples are illustrative. Participation uses the count-first v3 fixture; Company and Options keep their existing v2 raw records. The earlier HTML/static candidate is historical supporting evidence. No product implementation, merge or deployment is claimed.', 13))
    review_html = block('Review and continuity',
        text('The native first-pass product and taste reports were frozen before author rationale. Their reports remain unchanged; repairs and later captures have their own immutable artifact set and review. Native advisory critique is not a formal RIG receipt.') +
        text('The reference remains draft. The original Chinese chart-footer operation remains EFFECT_UNKNOWN on its original carrier. Scoped repaired-subset reviews cannot approve that excluded target or the full reference. F01, browser/consumer integration and formal review gates remain carried. Sector, Prophet and Refraction authority conditions retain their original source authority.', 13) +
        link('Exact native review status', BASE + 'paper/reviews/NATIVE_REVIEW_REPORT.md'))
    refs_html = block('Build and return through the existing owners',
        link('Source contract, producer mappings and integration acceptance', BASE + 'SOURCE_AND_DATA_CONTRACT.md') +
        link('Actual board IDs and current native captures', BASE + 'paper/NATIVE_BOARD_INDEX.md') +
        link('Retained originals and scoped candidate companions', BASE + 'paper/native-predecessor-bindings.json') +
        text('36 capabilities: 16 retain + 20 improve. 67 original Paper references: 25 retain + 42 improve. No removals or relocations. The four domain/source roles remain retained and unqualified until their owners provide the required real-path evidence.', 13))
    replacements = [
        ('readme', 'source', source_html), ('readme', 'limitations', limit_html),
        ('builder', 'review', review_html), ('builder', 'refs', refs_html),
    ]
    payload = {'schema': 'f02.readme-completion-inputs.v1', 'status': 'PREPARED_NOT_APPLIED',
               'file_id': FILE, 'source_runtime_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'observed_board_count': len(boards), 'observed_readme_page_id': readme['pageId'],
               'replacements': [{'board_key': k, 'board_id': boards[k]['id'], 'step_key': step,
                                 'target_node_id': boards[k]['steps'][step], 'html': html}
                                for k, step, html in replacements],
               'append_to_existing': [{'board_key': 'readme', 'board_id': readme['id'], 'steps': rows}],
               'writer_instructions': [
                   'Regenerate only after every intended board is in the saved runtime; confirm all referenced page IDs in fresh Paper reads.',
                   'Replace only the four owned groups and append one directory page row per write; refresh actual step IDs after replacement.',
                   'The URLs are exact page or Git source links. Native hyperlink activation is not asserted; preserve the full visible URL if the importer drops href.',
                   'Keep fit-content; capture final readme and builder after all groups. No original reference or global token is modified.',
               ]}
    target = PAPER / 'readme-completion-inputs.json'
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'path': str(target.relative_to(WORK)), 'boards': len(boards),
                      'replacements': len(replacements), 'directory_rows': len(rows),
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
