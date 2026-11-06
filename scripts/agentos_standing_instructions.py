"""Canonical Agent OS standing-instruction projector (pure stdlib).

Projects the optional canonical ``standing_instructions`` frontmatter field of
an already-parsed Mastermind workstream record into the public body schema
``mastermind.agentos.standing_instructions.v1``.

Bounded contract of this module:

- ``record`` is supplied by the caller (the parent owns canonical frontmatter
  parsing); this module performs no I/O, reads no source bytes, and consults
  no clock, grant store, scheduler or Runtime.
- ``source_ref`` is validated and echoed back as a detached mapping. The
  binding between ``content_sha256`` and the actual file bytes is owned by the
  parent's sealed source acquisition; this module never claims to hash those
  bytes.
- Arbitrary other workstream fields on ``record`` are permitted and are never
  returned.
- ``revision`` binds the exact canonical ``instruction_ref``/``text`` pair;
  it is not a digest of the source file.
- An accepted return value never implies that any instruction is enabled,
  running, enforced, or that any readiness changed; Runtime state is separate.
- Every malformed input raises ``ValueError('STANDING_INSTRUCTIONS_INVALID')``
  with no echo of the offending input. Over-cap public envelopes are refused,
  never truncated.
"""

import hashlib
import json
import re

__all__ = [
    'BODY_SCHEMA',
    'DECLARATION_NOT_DECLARED',
    'DECLARATION_SUPPLIED',
    'MAX_ENVELOPE_BYTES',
    'MAX_INSTRUCTIONS',
    'MAX_TEXT_CODEPOINTS',
    'SOURCE_REPOSITORY',
    'STANDING_INSTRUCTIONS_INVALID',
    'encode_public_envelope',
    'project_standing_instructions',
]

BODY_SCHEMA = 'mastermind.agentos.standing_instructions.v1'
DECLARATION_NOT_DECLARED = 'NOT_DECLARED'
DECLARATION_SUPPLIED = 'SUPPLIED'
STANDING_INSTRUCTIONS_INVALID = 'STANDING_INSTRUCTIONS_INVALID'

MAX_INSTRUCTIONS = 16
MAX_TEXT_CODEPOINTS = 4096
MAX_ENVELOPE_BYTES = 32768

SOURCE_REPOSITORY = 'mastermindx-market-intelligence/macro'
SOURCE_PATH_TEMPLATE = 'agentos/workstreams/WS-{key}.md'
SOURCE_REF_FIELDS = frozenset(
    ('repository', 'commit', 'path', 'content_sha256'))
INSTRUCTION_FIELDS = frozenset(('instruction_ref', 'text'))

_REF_PREFIX = 'INS:'
_MIN_KEY_CODEPOINTS = 2
_MAX_KEY_CODEPOINTS = 64
_COMMIT_RE = re.compile(r'[0-9a-f]{40}')
_SHA256_RE = re.compile(r'[0-9a-f]{64}')
# Upper kebab: one or more uppercase alnum segments joined by single hyphens.
_KEY_RE = re.compile(r'[A-Z0-9]+(?:-[A-Z0-9]+)*')
# LF, CR and TAB are permitted in instruction text; every other C0 control
# and DEL is rejected.
_PERMITTED_CONTROL_CODEPOINTS = frozenset((0x09, 0x0A, 0x0D))


def _invalid():
    return ValueError(STANDING_INSTRUCTIONS_INVALID)


def _canonical_key(value):
    """Return True for an upper-kebab identifier of 2..64 codepoints.

    Matching is a strict fullmatch, so identifiers carrying a trailing newline
    or any other suffix/prefix are rejected.
    """
    if not isinstance(value, str):
        return False
    if not _MIN_KEY_CODEPOINTS <= len(value) <= _MAX_KEY_CODEPOINTS:
        return False
    return _KEY_RE.fullmatch(value) is not None


def _validate_source_ref(source_ref, key):
    if not isinstance(source_ref, dict):
        raise _invalid()
    if frozenset(source_ref) != SOURCE_REF_FIELDS:
        raise _invalid()
    if source_ref['repository'] != SOURCE_REPOSITORY:
        raise _invalid()
    commit = source_ref['commit']
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        raise _invalid()
    content_sha256 = source_ref['content_sha256']
    if not isinstance(content_sha256, str) or \
            _SHA256_RE.fullmatch(content_sha256) is None:
        raise _invalid()
    path = source_ref['path']
    if not isinstance(path, str):
        raise _invalid()
    if path != SOURCE_PATH_TEMPLATE.format(key=key):
        raise _invalid()


def _validate_text(text):
    if not isinstance(text, str):
        raise _invalid()
    if len(text) > MAX_TEXT_CODEPOINTS:
        raise _invalid()
    if not text.strip():
        raise _invalid()
    for char in text:
        code = ord(char)
        if code in _PERMITTED_CONTROL_CODEPOINTS:
            continue
        if code < 0x20 or code == 0x7F:
            raise _invalid()


def _instruction_revision(instruction_ref, text):
    payload = {'instruction_ref': instruction_ref, 'text': text}
    try:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    except (TypeError, ValueError, UnicodeError):
        # Covers unserializable payloads, NaN under allow_nan=False, and lone
        # surrogates that cannot be encoded as UTF-8.
        raise _invalid() from None


def project_standing_instructions(record, source_ref):
    """Project the optional canonical standing_instructions field.

    Returns a detached body dict; absent field yields declaration
    NOT_DECLARED with an empty instruction list, while an authored empty
    list yields SUPPLIED with an empty instruction list. Raises
    ValueError('STANDING_INSTRUCTIONS_INVALID') for every malformed input and
    for any public envelope exceeding MAX_ENVELOPE_BYTES (refused, never
    truncated).
    """
    if not isinstance(record, dict):
        raise _invalid()
    key = record.get('key')
    if not _canonical_key(key):
        raise _invalid()
    _validate_source_ref(source_ref, key)

    instructions = []
    declaration = DECLARATION_NOT_DECLARED
    if 'standing_instructions' in record:
        raw_items = record['standing_instructions']
        if not isinstance(raw_items, list):
            raise _invalid()
        if len(raw_items) > MAX_INSTRUCTIONS:
            raise _invalid()
        declaration = DECLARATION_SUPPLIED
        seen_refs = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                raise _invalid()
            if frozenset(raw_item) != INSTRUCTION_FIELDS:
                raise _invalid()
            instruction_ref = raw_item['instruction_ref']
            text = raw_item['text']
            if not isinstance(instruction_ref, str):
                raise _invalid()
            if not instruction_ref.startswith(_REF_PREFIX):
                raise _invalid()
            if not _canonical_key(instruction_ref[len(_REF_PREFIX):]):
                raise _invalid()
            if instruction_ref in seen_refs:
                raise _invalid()
            seen_refs.add(instruction_ref)
            _validate_text(text)
            instructions.append({
                'instruction_ref': instruction_ref,
                'text': text,
                'revision': _instruction_revision(instruction_ref, text),
            })

    body = {
        'schema': BODY_SCHEMA,
        'selection': {'work_ref': 'WS:' + key},
        'source': {
            'repository': source_ref['repository'],
            'commit': source_ref['commit'],
            'path': source_ref['path'],
            'content_sha256': source_ref['content_sha256'],
        },
        'declaration': declaration,
        'instructions': instructions,
    }
    # Enforce the public envelope byte cap before returning: refuse overbound
    # rather than truncating. Also normalizes any unencodable content.
    encode_public_envelope(body)
    return body


def encode_public_envelope(body):
    """Return the canonical public envelope bytes for ``body``.

    The envelope is ``{"ok":true,"result":<body>}`` followed by a single
    newline, encoded as UTF-8 and never larger than MAX_ENVELOPE_BYTES.
    Raises ValueError('STANDING_INSTRUCTIONS_INVALID') for unserializable
    bodies (including NaN under allow_nan=False and lone surrogates) and for
    over-cap bodies.
    """
    envelope = {'ok': True, 'result': body}
    try:
        serialized = json.dumps(
            envelope,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(',', ':'),
        )
        encoded = serialized.encode('utf-8') + b'\n'
    except (TypeError, ValueError, UnicodeError):
        raise _invalid() from None
    if len(encoded) > MAX_ENVELOPE_BYTES:
        raise _invalid()
    return encoded
