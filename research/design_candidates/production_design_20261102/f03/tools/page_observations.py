"""Validate later Paper read evidence without changing the frozen F03 census."""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import math
import re
from datetime import datetime

EVIDENCE = 'paper/continuations/listed-page-expansion-20261104.json'
RAW = 'paper/continuations/listed-page-expansion-20261104.raw.json.gz'
SCHEMA = 'mastermind.f03.page_structure_observations.v1'
LIMITS = ('Structural metadata only; full content, visual quality, comments, assets, '
          'link preservation, product ownership, successor relationships, disposal, '
          'reference approval and input-path acceptance remain unestablished. '
          'The snapshot is a drift guard, not a full-content revision.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def objects(content):
    found = []
    for item in content:
        if item.get('type') != 'text':
            continue
        try:
            value = json.loads(item['text'])
        except (ValueError, TypeError):
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


def response(entry):
    raw = entry['response']
    require(not raw.get('isError'), 'Paper read returned an error')
    value = raw.get('structuredContent')
    if not isinstance(value, dict):
        matches = [x for x in objects(raw.get('content', [])) if 'state' in x]
        require(len(matches) == 1, 'missing or ambiguous Paper receipt')
        value = matches[0]
    require(value.get('state') == 'OBSERVED', 'read is not a successful observation')
    parts = objects(value['result']['content'])
    headers = [x for x in parts if 'file' in x]
    require(len(headers) == 1 and headers[0]['file']['id'] == entry['file_id'],
            'returned file identity differs from requested file')
    observed = entry['observed_at']
    require(isinstance(observed, str) and
            re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', observed),
            'observation time must use the fixed-millisecond UTC Z capture format')
    dt = datetime.fromisoformat(observed.replace('Z', '+00:00'))
    require(dt.tzinfo is not None, 'observation time needs an explicit timezone')
    return value, parts


def integer(value):
    return type(value) is int and value >= 0


def board(value):
    require(isinstance(value.get('id'), str) and
            re.fullmatch(r'[A-Za-z0-9]+-[A-Za-z0-9]+', value['id']), 'invalid board ID')
    require(isinstance(value.get('name'), str), 'invalid board name')
    require(integer(value.get('childCount')), 'invalid board child count')
    for key in ('width', 'height', 'worldX', 'worldY'):
        n = value.get(key)
        require(n is None or (type(n) in (int, float) and math.isfinite(n)),
                'geometry must be finite or unmeasured')
    return {key: value.get(key) for key in
            ('id', 'name', 'childCount', 'width', 'height', 'worldX', 'worldY')}


def normalize_capture(raw, baseline_pages):
    """Reconstruct evidence from actual read receipts; reject partial/mismatched lists."""
    require(set(raw) == {'page_reads', 'supplemental_reads'}, 'unexpected capture fields')
    allowed = {(p['paper_file_id'], p['paper_page_id']) for p in baseline_pages
               if p['listed_in_package'] and not p['expanded_in_package']}
    extras = {}
    for item in raw['supplemental_reads']:
        key = (item['file_id'], item['page_id'])
        require(key in allowed, 'supplement targets an unrelated page')
        require(item['tool'] in ('get_children', 'get_tree_summary', 'get_node_info'),
                'supplement is not a supported read')
        extras.setdefault(key, []).append(item)
    seen = set()
    pending = []
    for item in raw['page_reads']:
        key = (item['file_id'], item['page_id'])
        require(key in allowed and key not in seen, 'unrelated or duplicate page observation')
        value, parts = response(item)
        matches = [x for x in parts if 'pageId' in x]
        require(len(matches) == 1, 'missing or ambiguous page metadata')
        info = matches[0]
        require(info['pageId'] == key[1], 'returned page identity differs from requested page')
        require(info['url'] == 'https://app.paper.design/file/' + '/'.join(key),
                'page URL disagrees with exact identity')
        require(integer(info['nodeCount']) and integer(info['artboardCount']), 'invalid page counts')
        require(isinstance(info['fileName'], str) and isinstance(info['pageName'], str),
                'invalid observed names')
        identity = value['document']['identity']
        require(identity == {'kind': 'file-id', 'id': key[0]}, 'snapshot targets another file')
        guard = value['document']['snapshot_sha256']
        require(re.fullmatch('[0-9a-f]{64}', guard), 'invalid snapshot guard')
        initial = [board(x) for x in info['artboards']]
        boards = {x['id']: x for x in initial}
        require(len(boards) == len(initial), 'duplicate board ID within a page')
        require(len(initial) <= info['artboardCount'], 'more boards than reported')
        summaries = []
        used = []
        for extra in extras.get(key, []):
            _, parts2 = response(extra)
            if extra['tool'] == 'get_tree_summary':
                text = next(x['summary'] for x in parts2 if 'summary' in x)
                require('(' + info['rootNodeId'] + ')' in text.splitlines()[0],
                        'tree summary has the wrong root')
                ids = re.findall(r'^  \S+ .* \(([A-Za-z0-9]+-[A-Za-z0-9]+)\) ', text, re.M)
                require(len(ids) == len(set(ids)) == info['artboardCount'],
                        'root summary is incomplete or inconsistent')
                summaries.append(ids)
            elif extra['tool'] == 'get_node_info':
                nodes = [x for x in parts2 if x.get('id') == extra['node_id']]
                require(len(nodes) == 1, 'missing or ambiguous supplemental board')
                node = nodes[0]
                require(node['parentId'] == info['rootNodeId'], 'supplemental node is on another page')
                require(node['component'] == 'Frame', 'supplemental node is not an artboard frame')
                require(node['id'] not in boards, 'duplicate supplemental board')
                boards[node['id']] = board(node)
            # Truncated get_children receipts are retained as diagnosis, never completeness proof.
            used.append({'tool': extra['tool'], 'observed_at_utc': extra['observed_at'],
                         'node_id': extra.get('node_id'), 'response_sha256': digest(extra['response'])})
        require(len(boards) == info['artboardCount'], 'artboard list remains truncated')
        if len(initial) < info['artboardCount']:
            require(len(summaries) == 1 and set(summaries[0]) == set(boards),
                    'completed list is not bound to the complete root summary')
            ordered = [boards[node_id] for node_id in summaries[0]]
        else:
            require(not extras.get(key), 'unnecessary supplemental reads for a complete page')
            ordered = initial
        warnings = [x['text'] for x in value['result']['content']
                    if x.get('type') == 'text' and x.get('text', '').startswith('Warning:')]
        pending.append({'file_id': key[0], 'page_id': key[1], 'file_name': info['fileName'],
                        'page_name': info['pageName'], 'url': info['url'],
                        'root_node_id': info['rootNodeId'], 'observed_at_utc': item['observed_at'],
                        'completed_at_utc': max([item['observed_at']] + [x['observed_at_utc'] for x in used]),
                        'node_count': info['nodeCount'], 'artboard_count': info['artboardCount'],
                        'initial_returned_artboards': len(initial), 'artboards': ordered,
                        'snapshot_sha256': guard, 'response_sha256': digest(item['response']),
                        'completion_reads': used, 'warnings': warnings})
        seen.add(key)
    require(set(extras) <= seen, 'orphan supplemental read')
    return pending


def attach_page_observations(data, out):
    path = out / EVIDENCE
    if not path.exists():
        require('structural_observations' not in data['metadata'],
                'previously recorded structural evidence is missing')
        data['page_observations'] = []
        return
    evidence = json.loads(path.read_text())
    require(evidence['schema'] == SCHEMA and evidence['effect'] == 'READ_ONLY', 'wrong evidence contract')
    require(re.fullmatch('[0-9a-f]{40}', evidence['source_head']) and
            re.fullmatch('[0-9a-f]{40}', evidence['protected_procedure_sha']) and
            re.fullmatch('[0-9a-f]{64}', evidence['catalog_sha256']), 'invalid provenance pin')
    require(evidence['carrier'] == 'Mastermind Paper direct app', 'unexpected evidence carrier')
    require(evidence['raw_evidence'] == RAW, 'unexpected raw evidence path')
    compressed = (out / RAW).read_bytes()
    require(hashlib.sha256(compressed).hexdigest() == evidence['raw_evidence_sha256'],
            'raw evidence digest mismatch')
    raw = json.loads(gzip.decompress(compressed))
    pages = normalize_capture(raw, data['pages'])
    require(pages == evidence['pages'], 'observation projection differs from raw reads')
    require(evidence['qualification'] == LIMITS, 'observation qualification changed')
    total = sum(p['listed_in_package'] and not p['expanded_in_package'] for p in data['pages'])
    # Attach only after every row validates. No frozen page, board or owner is modified.
    data['page_observations'] = copy.deepcopy(pages)
    data['metadata']['structural_observations'] = {
        'evidence': EVIDENCE, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_head': evidence['source_head'], 'procedure_sha': evidence['protected_procedure_sha'],
        'baseline_listed_only_pages': total, 'observed_pages': len(pages),
        'remaining_pages': total - len(pages), 'observed_artboards': sum(p['artboard_count'] for p in pages),
        'zero_artboard_pages': sum(p['artboard_count'] == 0 for p in pages),
        'warning_files': len({p['file_id'] for p in pages if p['warnings']}),
        'qualification': LIMITS,
    }
