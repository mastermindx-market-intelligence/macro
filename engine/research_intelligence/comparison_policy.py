"""Root-sealed descriptive qualification policy, under the existing runtime owner.

Follows protected Mastermind 2a2216e integrations/research_read_mcp/entitlement.py
file-custody pattern without importing its identity/control plane or reusing its
content grant. This policy approves exact adjudications, never authenticates a
Brain user. Existing server context still supplies identity/PRO/surface/scope.
No file is opened at import or construction. There is no policy writer/installer,
credential, enrollment route, or permissive default in this module.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
import stat
import time

from engine.research_intelligence.comparison_qualification import (
    QualificationAuthority, validate_record, _hash, _text,
)
from engine.research_intelligence.store import _canonical_json_bytes, _decode_json_object

SCHEMA = "mastermind.research_intelligence.comparison_policy.v1"
POLICY_ID = "research-vault-descriptive-comparison-v1"
DEFAULT_PATH = "/etc/mastermind/research-comparison-qualification-policy.json"
MAX_BYTES = 64 * 1024
MAX_ENTRIES = 64


class PolicyRefused(ValueError):
    def __init__(self): super().__init__("research comparison policy refused")


def _refuse(): raise PolicyRefused()


def _read_policy_bytes(path, *, expected_owner_uid=0):
    """Bounded nonblocking/nofollow read, verified before/open/after/close.

    expected_owner_uid exists for the same deterministic filesystem tests as
    the incumbent loader. The production policy adapter always supplies 0.
    """
    if type(path) is not str or not path.startswith('/') or '\x00' in path or type(expected_owner_uid) is not int:
        _refuse()
    flags = [getattr(os, key, 0) for key in ('O_NOFOLLOW', 'O_CLOEXEC', 'O_NONBLOCK')]
    if not all(flags): _refuse()
    before = os.lstat(path)
    def valid(info):
        return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_uid == expected_owner_uid and not stat.S_IMODE(info.st_mode) & 0o022
                and 0 < info.st_size <= MAX_BYTES)
    if not valid(before): _refuse()
    fd = os.open(path, os.O_RDONLY | flags[0] | flags[1] | flags[2])
    try:
        opened = os.fstat(fd)
        if (not valid(opened) or opened.st_dev != before.st_dev or opened.st_ino != before.st_ino
                or opened.st_size != before.st_size or opened.st_mode != before.st_mode or os.get_inheritable(fd)):
            _refuse()
        chunks = []; remaining = opened.st_size
        while remaining:
            chunk = os.read(fd, min(4096, remaining))
            if not chunk: _refuse()
            chunks.append(chunk); remaining -= len(chunk)
        if os.read(fd, 1): _refuse()
        after_open = os.fstat(fd)
        if (after_open.st_size, after_open.st_mtime_ns, after_open.st_ctime_ns) != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
            _refuse()
        raw = b''.join(chunks)
    finally:
        os.close(fd)  # close failure refuses, never a successful policy read
    after = os.lstat(path)
    fields = ('st_dev', 'st_ino', 'st_uid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(after, k) != getattr(before, k) for k in fields): _refuse()
    return raw


def parse_policy(raw, *, now, expected_sha256=None):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES or type(now) is not int or now < 0:
        _refuse()
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != _hash(expected_sha256): _refuse()
    obj = _decode_json_object(raw, code='comparison_policy_invalid', label='comparison policy')
    if (set(obj) != {'schema', 'policy_id', 'authorization_provenance', 'entries'}
            or obj['schema'] != SCHEMA or obj['policy_id'] != POLICY_ID): _refuse()
    _text(obj['authorization_provenance'], 2000)
    entries = obj['entries']
    if type(entries) is not list or not 0 < len(entries) <= MAX_ENTRIES: _refuse()
    seen = set()
    for entry in entries:
        if type(entry) is not dict or set(entry) != {'qualification_sha256', 'adjudicator_id', 'review_sha256', 'audience', 'expires_at'}:
            _refuse()
        ref = _hash(entry['qualification_sha256']); _hash(entry['review_sha256']); _text(entry['adjudicator_id'], 200)
        if (ref in seen or entry['audience'] != 'brain_pro' or type(entry['expires_at']) is not int or entry['expires_at'] <= now):
            _refuse()
        seen.add(ref)
    return obj


class _RootOperatorContext:
    """Process-local operator context; possession alone grants nothing."""


def root_operator_context():
    """Explicit operator authoring only; no client route calls this function."""
    if os.geteuid() != 0: _refuse()
    return _RootOperatorContext()


class SealedQualificationPolicy:
    def __init__(self, path=DEFAULT_PATH, *, clock=None, expected_sha256=None):
        self.path = path
        self.clock = clock if clock is not None else lambda: int(time.time())
        self.expected_sha256 = expected_sha256

    def _load(self):
        return parse_policy(_read_policy_bytes(self.path, expected_owner_uid=0),
                            now=self.clock(), expected_sha256=self.expected_sha256)

    @staticmethod
    def _matches(entry, record, ref):
        return (entry['qualification_sha256'] == ref
                and entry['adjudicator_id'] == record['review']['adjudicator_id']
                and entry['review_sha256'] == hashlib.sha256(_canonical_json_bytes(record['review'])).hexdigest()
                and hashlib.sha256(_canonical_json_bytes(record)).hexdigest() == ref)

    def authorize_read(self, caller, record, ref):
        try:
            from engine.research_vault.read_service import ServerReadContext
            if (type(caller) is not ServerReadContext or not caller.principal_id or caller.entitlement != 'pro'
                    or caller.surface != 'brain' or 'find_evidence' not in caller.scopes): return False
            record = validate_record(record)
            if record["state"] != "QUALIFIED": return False
            return any(self._matches(entry, record, ref) for entry in self._load()['entries'])
        except Exception:
            return False

    def authorize_write(self, actor, proposal):
        """Root operator + root-sealed exact proposed content approval required.

        The principal is derived from the policy, never trusted from actor JSON.
        The operator installs the policy only after real source adjudication.
        This module neither grants that OS identity nor creates that policy.
        """
        try:
            if type(actor) is not _RootOperatorContext or os.geteuid() != 0: return None
            for entry in self._load()['entries']:
                candidate = deepcopy(proposal)
                candidate['review']['adjudicator_id'] = entry['adjudicator_id']
                record = validate_record(candidate)
                ref = hashlib.sha256(_canonical_json_bytes(record)).hexdigest()
                if self._matches(entry, record, ref): return entry['adjudicator_id']
            return None
        except Exception:
            return None

    def authority(self):
        return QualificationAuthority(self.authorize_write, self.authorize_read)
