"""W4 best-effort authored metadata. No execution decisions, network, or lifecycle state."""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import shlex
import sys
import subprocess
import tempfile

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from scripts import agentos as aos
from lib import pr_linkage_validator as linkage


def _report(code, *, changed=False, **fields):
    return dict(schema='agentos.ship_capture.v1', enforcement='REPORT_ONLY',
                code=code, changed=changed, **fields)


def _now(now):
    return now or dt.datetime.now(dt.timezone.utc)


def _regular(path, root):
    try:
        path.relative_to(root)
        path.resolve(strict=True).relative_to(root)
    except (ValueError, OSError):
        return False
    return not any(p.is_symlink() for p in [path, *path.parents] if p != root.parent) and path.is_file()


def _front(text):
    match = aos.FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError('malformed frontmatter')
    # Aliases and duplicate keys make a narrow edit's semantic footprint ambiguous.
    if any(isinstance(t, (aos.yaml.tokens.AliasToken, aos.yaml.tokens.AnchorToken))
           for t in aos.yaml.scan(match.group(1))):
        raise ValueError('aliased frontmatter')
    node = aos.yaml.compose(match.group(1), Loader=aos.yaml.SafeLoader)
    def check(n):
        if isinstance(n, aos.yaml.MappingNode):
            keys = [k.value for k, _ in n.value]
            if len(keys) != len(set(keys)):
                raise ValueError('duplicate frontmatter key')
            for _, value in n.value:
                check(value)
        elif isinstance(n, aos.yaml.SequenceNode):
            for value in n.value:
                check(value)
    check(node)
    return match, node


def _records(root):
    directory = root / 'agentos/workstreams'
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError('missing store')
    paths = sorted(directory.glob('*.md'))
    if not paths or len(paths) > 512:
        raise ValueError('missing or oversized workstream set')
    records = {}
    for path in paths:
        if not _regular(path, root) or path.stat().st_size > 262144:
            raise ValueError('unsafe workstream source')
        text = path.read_text(encoding='utf-8')
        _front(text)
        rec, _ = aos.parse_record(path)
        if any(p.hard for p in aos.check_workstream(rec, path, None)):
            raise ValueError('malformed workstream')
        key = rec['key']
        if key in records:
            raise ValueError('duplicate workstream')
        records[key] = (rec, path, text)
    return records


def _current_claim(rec, branch, now):
    claim = rec.get('claim')
    if not isinstance(claim, dict) or claim.get('by') != branch:
        return False
    expires = aos._parse_moment(str(claim.get('expires', '')))
    return bool(expires and expires > now)


def _header(body):
    manifest = linkage.loads_strict((aos._ROOT / 'config/pr_linkage_rules.v1.json').read_bytes())
    fields, locations, _, defects, _ = linkage.parse_header(body, manifest['limits'], infer_scattered=False)
    if defects or any(len(v) != 1 for v in locations.values()):
        raise ValueError('noncanonical header')
    ws, wave = fields['Workstream'], fields['Wave']
    if not isinstance(ws, str) or not re.fullmatch(r'WS:[A-Z0-9]+(?:-[A-Z0-9]+)*', ws):
        raise ValueError('noncanonical workstream')
    if not isinstance(wave, str) or not re.fullmatch(manifest['grammar']['field_patterns']['Wave'], wave):
        raise ValueError('noncanonical wave')
    return ws[3:], wave


def _bind(records, branch, paths, now):
    if not isinstance(paths, list) or not paths or len(paths) > 10000:
        return None, 'unbound_paths'
    for path in paths:
        if (not isinstance(path, str) or not path or '\\' in path or '\0' in path
                or PurePosixPath(path).is_absolute() or '..' in PurePosixPath(path).parts
                or str(PurePosixPath(path)) != path):
            return None, 'unsafe_path'
    claimed = [key for key, (rec, _, _) in records.items() if _current_claim(rec, branch, now)]
    if claimed:
        return (claimed[0], 'claim') if len(claimed) == 1 else (None, 'ambiguous_claim')
    if not paths or len(paths) > 10000:
        return None, 'unbound_paths'
    sole = set()
    for path in paths:
        if not isinstance(path, str) or not path or '\\' in path or '\0' in path:
            return None, 'unsafe_path'
        parts = PurePosixPath(path)
        if parts.is_absolute() or '..' in parts.parts or str(parts) != path:
            return None, 'unsafe_path'
        owners = set()
        for key, (rec, _, _) in records.items():
            for pattern in rec.get('owns_paths', []):
                resolved = aos._resolve_path(pattern, rec)
                if resolved and resolved[0] == 'macro' and aos._glob_match(resolved[1], path):
                    owners.add(key)
        if len(owners) != 1:
            return None, 'ambiguous_or_unowned_path'
        sole.update(owners)
    return (next(iter(sole)), 'paths') if len(sole) == 1 else (None, 'multiple_owners')


def _mapping(node):
    return {k.value: (k, v) for k, v in node.value}


def _capture_text(text, wave_id, pr):
    match, node = _front(text)
    waves = _mapping(node)['waves'][1]
    selected = [w for w in waves.value if _mapping(w)['id'][1].value == wave_id]
    if len(selected) != 1:
        raise ValueError('ambiguous wave')
    fields = _mapping(selected[0])
    key, value = fields['status']
    if value.style is not None:
        # Quoted/block scalar layouts are valid records but not a safe automatic edit.
        raise ValueError('unsupported wave layout')
    start, end = match.start(1) + value.start_mark.index, match.start(1) + value.end_mark.index
    result = text[:start] + 'awaiting_ci' + text[end:]
    line_end = result.find('\n', start)
    indent = ' ' * key.start_mark.column
    return result[:line_end + 1] + f'{indent}pr: {pr}\n' + result[line_end + 1:]


def _replace(path, before, after, root):
    """Atomic local edit; an inode lock and byte comparison protect cooperative writers."""
    if not _regular(path, root):
        raise ValueError('unsafe source')
    name = None
    with path.open('r', encoding='utf-8') as source:
        fcntl.flock(source, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            inode = os.fstat(source.fileno())
            if path.stat().st_ino != inode.st_ino or source.read() != before:
                raise ValueError('source changed since observation')
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as target:
                name = target.name
                target.write(after.encode('utf-8'))
                target.flush()
                os.fsync(target.fileno())
                os.fchmod(target.fileno(), stat.S_IMODE(inode.st_mode))
            if path.read_text(encoding='utf-8') != before:
                raise ValueError('source changed before replacement')
            os.replace(name, path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)
            fcntl.flock(source, fcntl.LOCK_UN)


def capture_pr(root, *, branch, body, pr, paths, now=None):
    """Capture supplied observations only. Caller owns PR/branch acquisition provenance."""
    try:
        root = Path(root).resolve()
        if not branch or branch in {'main', 'master', 'HEAD'} or type(pr) is not int or pr < 1:
            return _report('CAPTURE_UNBOUND')
        records = _records(root)
        key, binding = _bind(records, branch, paths, _now(now))
        body_key, wave_id = _header(body)
        if not key or key != body_key:
            return _report('CAPTURE_UNBOUND', binding=binding)
        rec, path, text = records[key]
        waves = [w for w in rec['waves'] if w['id'] == wave_id]
        if len(waves) != 1:
            return _report('CAPTURE_UNBOUND', binding=binding)
        wave = waves[0]
        if pr in aos._wave_prs(wave):
            return _report('CAPTURE_UNCHANGED', binding=binding, workstream=key, wave=wave_id, pr=pr)
        if 'pr' in wave or wave['status'] not in {'todo', 'in_progress'}:
            return _report('CAPTURE_CONFLICT', binding=binding)
        after = _capture_text(text, wave_id, pr)
        _front(after)
        _replace(path, text, after, root)
        return _report('CAPTURE_UNCOMMITTED', changed=True, binding=binding,
                       workstream=key, wave=wave_id, pr=pr,
                       message='Include this scoped record edit in the next normal commit and push; it is not durable yet.')
    except Exception as exc:
        return _report('CAPTURE_UNRECORDED', error=type(exc).__name__)


def edit_claim(root, *, workstream, branch, release=False, now=None):
    """Author an advisory note, never a lease. Never erase another branch's note."""
    try:
        root, now = Path(root).resolve(), _now(now)
        if not branch or branch in {'main', 'master', 'HEAD'}:
            return _report('CLAIM_UNBOUND')
        records = _records(root)
        if workstream not in records:
            return _report('CLAIM_UNBOUND')
        rec, path, text = records[workstream]
        existing = rec.get('claim')
        if existing and existing.get('by') != branch:
            return _report('CLAIM_CONFLICT')
        if release and not existing:
            return _report('CLAIM_UNCHANGED')
        match, node = _front(text)
        fields = _mapping(node)
        if 'claim' in fields:
            key, value = fields['claim']
            start = match.start(1) + key.start_mark.index
            end = match.start(1) + value.end_mark.index
        else:
            start = end = match.end(1) + 1
        stamp = lambda value: value.strftime('%Y-%m-%dT%H:%M:%SZ')
        addition = '' if release else aos.yaml.safe_dump({'claim': {
            'by': branch, 'at': stamp(now), 'expires': stamp(now + dt.timedelta(hours=12))}}, sort_keys=False)
        after = text[:start] + addition + text[end:]
        # Reparse before replacement: unsupported flow layouts must never corrupt a record.
        front, _ = _front(after)
        proposed = aos._yaml_safe_load(front.group(1))
        if any(p.hard for p in aos.check_workstream(proposed, path, None)):
            raise ValueError('unsupported claim layout')
        _replace(path, text, after, root)
        return _report('CLAIM_UNCOMMITTED', changed=True, workstream=workstream,
                       advisory=True, message='Advisory author note only; not liveness or authority. Commit normally.')
    except Exception as exc:
        return _report('CLAIM_UNRECORDED', error=type(exc).__name__)


def _git(root, *args, timeout=3):
    result = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=timeout, check=True)
    return result.stdout.rstrip('\n')


def _creation_body(root, command):
    if not isinstance(command, str) or len(command) > 262144 or '$' in command or '`' in command:
        return None
    lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|<>()')
    lexer.whitespace_split = True
    lexer.commenters = ''
    words = list(lexer)
    if words[:3] != ['gh', 'pr', 'create']:
        return None
    values, switches = {}, {'--draft', '-d'}
    options = {'--title': 'title', '-t': 'title', '--body': 'body', '-b': 'body',
               '--body-file': 'body_file', '-F': 'body_file', '--base': 'base', '-B': 'base'}
    i = 3
    while i < len(words):
        flag = words[i]
        if flag in switches:
            i += 1
            continue
        if flag not in options or i + 1 == len(words):
            return None
        name = options[flag]
        if name in values:
            return None
        values[name] = words[i + 1]
        i += 2
    if values.get('base', 'main') != 'main' or ('body' in values) == ('body_file' in values):
        return None
    if 'body' in values:
        return values['body']
    path = root / values['body_file']
    if not _regular(path, root) or path.stat().st_size > 262144:
        return None
    return path.read_text(encoding='utf-8')


def _origin(root):
    remote = _git(root, 'remote', 'get-url', 'origin')
    match = re.fullmatch(r'(?:git@github\.com:|https://github\.com/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', remote)
    if not match:
        raise ValueError('unsupported origin')
    return match.group(1)


def _paths(root, *, timeout=3):
    raw = _git(root, 'diff', '--name-status', '-z', '--find-renames', 'refs/remotes/origin/main...HEAD', timeout=timeout)
    if len(raw) > 1048576:
        raise ValueError('oversized changed path observation')
    fields = raw.split('\0')
    if fields[-1] != '':
        raise ValueError('truncated changed path observation')
    fields.pop()
    paths, i = [], 0
    while i < len(fields):
        status = fields[i]
        count = 2 if re.fullmatch(r'[RC][0-9]{1,3}', status) else 1 if status in {'A', 'M', 'D', 'T'} else 0
        if not count or i + count >= len(fields):
            raise ValueError('unknown changed path observation')
        paths.extend(fields[i + 1:i + count + 1])
        i += count + 1
    return list(dict.fromkeys(paths))


def hook_event(root, payload, *, now=None):
    try:
        root = Path(root).resolve()
        if payload.get('hook_event_name') == 'Stop':
            return handoff_reminder(root, branch=_git(root, 'branch', '--show-current'), now=now)
        if payload.get('hook_event_name') != 'PostToolUse' or payload.get('tool_name') != 'Bash':
            return _report('CAPTURE_UNSUPPORTED')
        body = _creation_body(root, (payload.get('tool_input') or {}).get('command'))
        if body is None:
            return _report('CAPTURE_UNSUPPORTED')
        response = payload.get('tool_response')
        if not isinstance(response, dict) or response.get('interrupted') is not False:
            return _report('CAPTURE_UNBOUND')
        if response.get('exitCode', response.get('exit_code', 0)) != 0 or response.get('is_error'):
            return _report('CAPTURE_UNBOUND')
        branch = _git(root, 'branch', '--show-current')
        origin = _origin(root)
        url = re.fullmatch(r'https://github\.com/' + re.escape(origin) + r'/pull/([1-9][0-9]*)',
                           str(response.get('stdout', '')).strip())
        if not url or not branch:
            return _report('CAPTURE_UNBOUND')
        return capture_pr(root, branch=branch, body=body, pr=int(url[1]), paths=_paths(root), now=now)
    except Exception as exc:
        return _report('CAPTURE_UNRECORDED', error=type(exc).__name__)


def handoff_reminder(root, *, branch, now=None):
    """Report only. A different/dirty/old-session handoff cannot stand in for this branch."""
    try:
        root = Path(root).resolve()
        records = _records(root)
        claimed = [key for key, (rec, _, _) in records.items() if _current_claim(rec, branch, _now(now))]
        if len(claimed) != 1:
            return _report('HANDOFF_UNBOUND')
        key = claimed[0]
        claim_at = aos._parse_moment(str(records[key][0]['claim'].get('at', '')))
        directory = root / 'agentos/handoffs'
        candidates = set(directory.glob(f'{key}-*.md')) | set(directory.glob(f'WS-{key}-*.md'))
        for path in sorted(candidates):
            if not _regular(path, root) or path.stat().st_size > 262144:
                continue
            try:
                record, body = aos.parse_record(path)
                if record.get('workstream') != f'WS:{key}' or record.get('session') != branch:
                    continue
                if any(p.hard for p in aos.check_handoff({**record, "_body": body}, path)):
                    continue
                relative = path.relative_to(root).as_posix()
                _git(root, 'ls-files', '--error-unmatch', '--', relative)
                _git(root, 'diff', '--quiet', 'HEAD', '--', relative)
                committed_at = aos._parse_moment(_git(root, 'log', '-1', '--format=%cI', 'HEAD', '--', relative))
                if not claim_at or not committed_at or committed_at < claim_at:
                    continue
                return _report('HANDOFF_COMMITTED', workstream=key, path=relative)
            except (ValueError, OSError, subprocess.SubprocessError):
                continue
        return _report('HANDOFF_REMINDER', workstream=key,
                       message='This branch has an advisory claim but no valid committed handoff for it. Write and commit a durable handoff when the protocol requires one; this reminder does not block execution.')
    except Exception as exc:
        return _report('HANDOFF_UNAVAILABLE', error=type(exc).__name__)


def command(args):
    """All knowledge-assistance outcomes exit zero; this is never an execution gate."""
    try:
        root = Path(args.repo).resolve() if args.repo else aos._ROOT
        if getattr(args, 'hook', False):
            raw = sys.stdin.read(1048577)
            if len(raw) > 1048576:
                raise ValueError('oversized payload')
            payload = json.loads(raw)
            cwd = Path(payload.get('cwd', str(root))).resolve()
            target = Path(_git(cwd, 'rev-parse', '--show-toplevel')).resolve()
            if root != aos._ROOT:
                result = _report('CAPTURE_SOURCE_MISMATCH')
            elif target != root and args.command == 'ship-report':
                # The existing launcher may start hooks from the primary checkout.
                # Delegate this READ-ONLY reminder once, only inside the same Git store.
                output = {}
                try:
                    source_common = _git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                    target_common = _git(target, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                    script = target / 'scripts/agentos.py'
                    if (not payload.get('_agentos_delegated') and source_common and target_common
                            and Path(source_common).resolve() == Path(target_common).resolve()
                            and _regular(script, target)):
                        child = subprocess.run([sys.executable, str(script), 'ship-report', '--hook'],
                            cwd=target, input=json.dumps({**payload, '_agentos_delegated': True}),
                            text=True, capture_output=True, timeout=5)
                        if child.returncode == 0 and len(child.stdout) < 16384:
                            candidate = json.loads(child.stdout)
                            if isinstance(candidate, dict) and set(candidate) <= {'systemMessage'} and all(isinstance(v, str) for v in candidate.values()):
                                output = candidate
                except Exception:
                    pass
                print(json.dumps(output))
                return 0
            elif target != root:
                result = _report('CAPTURE_SOURCE_MISMATCH')
            else:
                result = hook_event(root, payload)
        else:
            # Attended commands can wait for local storage; native hooks keep 3s reads.
            branch = _git(root, 'branch', '--show-current', timeout=60)
            if args.command == 'ship-capture':
                if args.body_file.stat().st_size > 262144:
                    raise ValueError('oversized body')
                result = capture_pr(root, branch=branch, body=args.body_file.read_text(encoding='utf-8'),
                                    pr=args.pr, paths=_paths(root, timeout=60))
            elif args.command == 'ship-report':
                result = handoff_reminder(root, branch=branch)
            else:
                result = edit_claim(root, workstream=args.workstream, branch=branch,
                                    release=args.command == 'release')
        if getattr(args, 'hook', False) and args.command == 'ship-report':
            # Separate Stop hook: exactly one native JSON object, never a decision.
            visible = result['code'] not in {'HANDOFF_COMMITTED', 'HANDOFF_UNBOUND', 'CAPTURE_SOURCE_MISMATCH'}
            print(json.dumps({'systemMessage': 'AGENT OS REPORT_ONLY: ' + result['code'] + '. ' + result.get('message', '')} if visible else {}))
        else:
            print(json.dumps(result, sort_keys=True))
    except Exception as exc:
        if getattr(args, 'hook', False) and args.command == 'ship-report':
            print('{}')
        else:
            print(json.dumps(_report('CAPTURE_UNRECORDED', error=type(exc).__name__)))
    return 0
