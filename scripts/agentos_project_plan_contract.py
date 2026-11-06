"""Pure content/reference/lineage validator for Agent OS project-plan adoption.

Scope (parent-owned integration excluded here):

* ``validate_source_ref`` / ``bind_source_ref`` -- closed-shaped immutable
  source references and exact raw-byte correspondence.  References and
  digests are recorded facts only; nothing here fetches, reads, resolves or
  qualifies a source and nothing here grants adoption authority.
* ``validate_adoption`` / ``validate_proposal`` -- closed metadata/header
  contracts for the optional ``project_plan_adoption`` DEC extension and the
  matching project-plan proposal header.
* ``select_current_adoption`` -- pure selection of the single current
  adoption from already-parsed DEC records using exact source/target and
  reciprocal ``supersedes`` / ``superseded_by`` lineage.  Timestamps are
  never read and never elect a head.
* ``require_expected_predecessor`` / ``require_proposal_base`` -- stale-base
  guards.  The caller still owns the real write compare-and-swap and source
  qualification; these checks alone create no write and never claim that an
  evidence body was read.

Contract rules baked in here:

* stdlib only; no I/O, network, Git, filesystem, clock, randomness or
  environment access; deterministic order; plain dict/list/bytes only.
* every rejection raises :class:`PlanContentError` whose ``code`` and
  ``str()`` are one closed value-free code; messages never echo a question,
  rationale, body, path, digest or revision value.
* all returned dicts/lists are freshly built ("detached"): mutating caller
  inputs afterwards cannot change a returned value, and mutating a returned
  value cannot change caller records or a second validation result.
* raw bytes are hashed exactly as supplied (line endings and BOM included);
  no JSON/YAML reserialization or Unicode normalization ever feeds a digest.
* legacy DEC records without ``project_plan_adoption`` metadata are ignored
  by lineage selection and stay unaffected.
* no ``accepted`` boolean, current/latest registry, status enum, grant,
  lease, Job or admission field is introduced or honoured; extra keys are
  rejected.

Closed reference shapes used across this module:

* work ref -- ``WS:`` + UPPER-KEBAB, key length 2..64.
* decision ref -- ``DEC:`` + UPPER-KEBAB, key length 2..128.
* scoped decision key -- canonical record ``key`` in UPPER-KEBAB, length 2..128.
* proposal id -- UPPER-KEBAB, length 2..128.

Closed macro workstream record path rule: any macro repository source
reference whose path lies inside ``agentos/workstreams/`` (case-insensitive
directory prefix) must equal ``agentos/workstreams/WS-<KEY>.md`` for
the selected work ref.  Cross-workstream substitution and case games are
rejected.  Other source-path ownership is parent-qualified, not invented
here.

Closed rejection-code mapping used by this module:

* ``INVALID_SOURCE_REF`` -- malformed source reference or source path.
* ``SOURCE_BYTES_MISMATCH`` -- raw bytes not exact ``bytes`` of the allowed
  size, not decodable UTF-8, or not matching the recorded digest (bound
  bytes and proposal candidate bytes alike).
* ``INVALID_ADOPTION`` -- malformed adoption metadata, malformed scoped
  record identity/affects, malformed lineage field types, malformed
  ``select_current_adoption`` container or ``current`` shape.
* ``INVALID_PROPOSAL`` -- malformed proposal header or candidate text that
  is not UTF-8.
* ``WORK_REF_MISMATCH`` -- a caller-supplied work ref is not a strict work
  ref, or a metadata/header work ref disagrees with the selected target.
* ``LINEAGE_CONFLICT`` -- contradictory lineage: broken reciprocal link,
  self/cycle, branch, competing or disconnected heads, duplicate scoped
  key, secret extra supersession, claimed-target versus ``affects``
  disagreement, malformed lineage field types.
* ``LINEAGE_INCOMPLETE`` -- a named predecessor or successor is missing from
  the scoped graph.
* ``STALE_PREDECESSOR`` -- candidate predecessor/base disagrees with the
  selected current adoption.
* ``CONTENT_OVER_BUDGET`` -- proposal candidate bytes over the byte budget.
"""

import hashlib

__all__ = [
    "ADOPTION_SCHEMA",
    "CONTENT_ERROR_CODES",
    "MAX_CANDIDATE_BYTES",
    "MAX_SOURCE_BYTES",
    "PROPOSAL_SCHEMA",
    "PlanContentError",
    "bind_source_ref",
    "require_expected_predecessor",
    "require_proposal_base",
    "select_current_adoption",
    "validate_adoption",
    "validate_proposal",
    "validate_source_ref",
]

ADOPTION_SCHEMA = "agentos.project_plan_adoption.v1"
PROPOSAL_SCHEMA = "agentos.project_plan_proposal.v1"

MACRO_REPOSITORY = "mastermindx-market-intelligence/macro"
MASTERMIND_REPOSITORY = "mastermindx-market-intelligence/Mastermind"
SOURCE_REPOSITORIES = (MACRO_REPOSITORY, MASTERMIND_REPOSITORY)

SOURCE_REF_KEYS = ("repository", "path", "commit", "content_sha256")
ADOPTION_KEYS = (
    "schema",
    "work_ref",
    "adopted_source",
    "predecessor",
    "proposal_source",
    "display_revision",
)
PROPOSAL_KEYS = (
    "schema",
    "proposal_id",
    "work_ref",
    "base_adoption",
    "base_source",
    "candidate_sha256",
    "rationale",
    "evidence",
)
CURRENT_KEYS = ("decision_ref", "adoption")

WS_PREFIX = "WS:"
DEC_PREFIX = "DEC:"

MACRO_WORKSTREAMS_DIR = "agentos/workstreams/"
PATH_SUFFIX = ".md"

MAX_PATH_CHARS = 512
MAX_WORK_REF_KEY_CHARS = 64
MAX_KEY_CHARS = 128
MAX_DISPLAY_REVISION_CHARS = 128
MAX_RATIONALE_CHARS = 4096
MAX_EVIDENCE_REFS = 32
MAX_RECORDS = 128
MAX_SOURCE_BYTES = 262144
MAX_CANDIDATE_BYTES = 131072

INVALID_SOURCE_REF = "INVALID_SOURCE_REF"
SOURCE_BYTES_MISMATCH = "SOURCE_BYTES_MISMATCH"
INVALID_ADOPTION = "INVALID_ADOPTION"
INVALID_PROPOSAL = "INVALID_PROPOSAL"
WORK_REF_MISMATCH = "WORK_REF_MISMATCH"
LINEAGE_CONFLICT = "LINEAGE_CONFLICT"
LINEAGE_INCOMPLETE = "LINEAGE_INCOMPLETE"
STALE_PREDECESSOR = "STALE_PREDECESSOR"
CONTENT_OVER_BUDGET = "CONTENT_OVER_BUDGET"

CONTENT_ERROR_CODES = frozenset(
    (
        INVALID_SOURCE_REF,
        SOURCE_BYTES_MISMATCH,
        INVALID_ADOPTION,
        INVALID_PROPOSAL,
        WORK_REF_MISMATCH,
        LINEAGE_CONFLICT,
        LINEAGE_INCOMPLETE,
        STALE_PREDECESSOR,
        CONTENT_OVER_BUDGET,
    )
)

_LOWER_HEX = frozenset("0123456789abcdef")
_KEBAB_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_FORBIDDEN_CONTROL_CHARS = ("\x00", "\n", "\r")


class PlanContentError(ValueError):
    """Value-free content-contract rejection.

    ``code`` and the string form of the error are one closed value-free code
    from :data:`CONTENT_ERROR_CODES`; no offending input value is echoed.
    """

    def __init__(self, code):
        if code not in CONTENT_ERROR_CODES:
            raise ValueError("PLAN_CONTENT_ERROR_CODE")
        self.code = code
        ValueError.__init__(self, code)


def _fail(code):
    raise PlanContentError(code)


def _is_str(value):
    return isinstance(value, str)


def _require_dict(value, code):
    if not isinstance(value, dict):
        _fail(code)
    return value


def _require_exact_keys(value, expected, code):
    if set(value) != set(expected):
        _fail(code)


def _is_lower_hex(value, size):
    return (
        _is_str(value)
        and len(value) == size
        and all(char in _LOWER_HEX for char in value)
    )


def _is_kebab(value):
    if not _is_str(value) or not value:
        return False
    for part in value.split("-"):
        if not part:
            return False
        if not all(char in _KEBAB_CHARS for char in part):
            return False
    return True


def _is_kebab_key(value):
    return _is_kebab(value) and 2 <= len(value) <= MAX_KEY_CHARS


def _is_work_ref_form(value):
    if not _is_str(value) or not value.startswith(WS_PREFIX):
        return False
    if not 2 <= len(value[len(WS_PREFIX):]) <= MAX_WORK_REF_KEY_CHARS:
        return False
    return _is_kebab(value[len(WS_PREFIX):])


def _is_dec_ref_form(value):
    if not _is_str(value) or not value.startswith(DEC_PREFIX):
        return False
    return _is_kebab_key(value[len(DEC_PREFIX):])


def _dec_ref(key):
    return DEC_PREFIX + key


def _scoped_key(dec_ref):
    return dec_ref[len(DEC_PREFIX):]


def _workstream_key(work_ref):
    return work_ref[len(WS_PREFIX):]


def _ws_record_path(work_ref):
    return MACRO_WORKSTREAMS_DIR + "WS-" + _workstream_key(work_ref) + PATH_SUFFIX


def _validate_work_ref(value):
    """Validate a caller-supplied target work ref (raises ``WORK_REF_MISMATCH``)."""
    if not _is_work_ref_form(value):
        _fail(WORK_REF_MISMATCH)
    return value


def _validate_source_path(path):
    if not _is_str(path) or not path or len(path) > MAX_PATH_CHARS:
        _fail(INVALID_SOURCE_REF)
    if path.startswith("/"):
        _fail(INVALID_SOURCE_REF)
    for char in _FORBIDDEN_CONTROL_CHARS:
        if char in path:
            _fail(INVALID_SOURCE_REF)
    if "\\" in path:
        _fail(INVALID_SOURCE_REF)
    if not path.endswith(PATH_SUFFIX):
        _fail(INVALID_SOURCE_REF)
    for part in path.split("/"):
        if part in ("", ".", ".."):
            _fail(INVALID_SOURCE_REF)
    return path


def _detach_ref(ref):
    return {
        "repository": ref["repository"],
        "path": ref["path"],
        "commit": ref["commit"],
        "content_sha256": ref["content_sha256"],
    }


def _validate_source_ref_fields(value):
    """Validate a mapping already known to be a dict with exact source-ref keys."""
    _require_dict(value, INVALID_SOURCE_REF)
    _require_exact_keys(value, SOURCE_REF_KEYS, INVALID_SOURCE_REF)
    repository = value["repository"]
    if repository not in SOURCE_REPOSITORIES:
        _fail(INVALID_SOURCE_REF)
    _validate_source_path(value["path"])
    if not _is_lower_hex(value["commit"], 40):
        _fail(INVALID_SOURCE_REF)
    if not _is_lower_hex(value["content_sha256"], 64):
        _fail(INVALID_SOURCE_REF)
    return _detach_ref(value)


def validate_source_ref(value):
    """Return a detached validated source reference for ``value``.

    Pure shape check only: no query parameter, URL or path is ever fetched
    and no source availability or authority is asserted.
    """
    _require_dict(value, INVALID_SOURCE_REF)
    return _validate_source_ref_fields(value)


def _require_raw_bytes(raw_bytes, code):
    if not isinstance(raw_bytes, bytes) or isinstance(raw_bytes, bool):
        _fail(code)
    if not 1 <= len(raw_bytes) <= MAX_SOURCE_BYTES:
        _fail(code)
    try:
        raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        _fail(code)


def _sha256_hex(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def bind_source_ref(value, raw_bytes):
    """Return the detached validated reference when ``raw_bytes`` correspond.

    ``raw_bytes`` must be exact ``bytes`` of length 1..262144, decodable as
    UTF-8, and must hash (exact bytes: line endings and BOM included, no
    reserialization or normalization) to the recorded ``content_sha256``.
    This asserts byte correspondence only; it never asserts that the source
    is available, qualified or authoritative.
    """
    ref = validate_source_ref(value)
    _require_raw_bytes(raw_bytes, SOURCE_BYTES_MISMATCH)
    if _sha256_hex(raw_bytes) != ref["content_sha256"]:
        _fail(SOURCE_BYTES_MISMATCH)
    return ref


def _check_ws_path_ownership(ref, work_ref, code):
    """Enforce the closed macro workstream record path rule for one reference."""
    if ref["repository"] != MACRO_REPOSITORY:
        return
    path = ref["path"]
    if not path.lower().startswith(MACRO_WORKSTREAMS_DIR):
        return
    if path != _ws_record_path(work_ref):
        _fail(code)


def _validate_display_revision(value):
    if value is None:
        return None
    if not _is_str(value):
        _fail(INVALID_ADOPTION)
    if len(value) > MAX_DISPLAY_REVISION_CHARS:
        _fail(INVALID_ADOPTION)
    for char in _FORBIDDEN_CONTROL_CHARS:
        if char in value:
            _fail(INVALID_ADOPTION)
    if not value.strip():
        _fail(INVALID_ADOPTION)
    return value


def _validate_adoption_fields(value, work_ref):
    """Validate adoption fields of a dict with exact keys and a dict type."""
    if value["schema"] != ADOPTION_SCHEMA:
        _fail(INVALID_ADOPTION)
    ref_work_ref = value["work_ref"]
    if not _is_work_ref_form(ref_work_ref):
        _fail(INVALID_ADOPTION)
    if ref_work_ref != work_ref:
        _fail(WORK_REF_MISMATCH)
    adopted_source = _validate_source_ref_fields(value["adopted_source"])
    _check_ws_path_ownership(adopted_source, work_ref, INVALID_ADOPTION)
    predecessor = value["predecessor"]
    if predecessor is not None and not _is_dec_ref_form(predecessor):
        _fail(INVALID_ADOPTION)
    proposal_source = value["proposal_source"]
    if proposal_source is not None:
        checked = _validate_source_ref_fields(proposal_source)
        _check_ws_path_ownership(checked, work_ref, INVALID_ADOPTION)
    display_revision = _validate_display_revision(value["display_revision"])
    return {
        "schema": ADOPTION_SCHEMA,
        "work_ref": ref_work_ref,
        "adopted_source": adopted_source,
        "predecessor": predecessor,
        "proposal_source": _detach_ref(value["proposal_source"])
        if proposal_source is not None
        else None,
        "display_revision": display_revision,
    }


def validate_adoption(value, *, work_ref):
    """Return a detached closed adoption-metadata dict.

    ``work_ref`` is the selected target work ref; the metadata work ref must
    be a strict work ref and must equal it.  The result asserts recorded
    metadata shape only -- never adoption, acceptance or authority.
    """
    _validate_work_ref(work_ref)
    _require_dict(value, INVALID_ADOPTION)
    _require_exact_keys(value, ADOPTION_KEYS, INVALID_ADOPTION)
    return _validate_adoption_fields(value, work_ref)


def _validate_proposal_header(value, work_ref):
    """Validate proposal header fields of a dict with exact keys and dict type."""
    if value["schema"] != PROPOSAL_SCHEMA:
        _fail(INVALID_PROPOSAL)
    proposal_id = value["proposal_id"]
    if not _is_kebab(proposal_id) or not 2 <= len(proposal_id) <= MAX_KEY_CHARS:
        _fail(INVALID_PROPOSAL)
    ref_work_ref = value["work_ref"]
    if not _is_work_ref_form(ref_work_ref):
        _fail(INVALID_PROPOSAL)
    if ref_work_ref != work_ref:
        _fail(WORK_REF_MISMATCH)
    base_adoption = value["base_adoption"]
    if base_adoption is not None and not _is_dec_ref_form(base_adoption):
        _fail(INVALID_PROPOSAL)
    if value["base_source"] is None:
        _fail(INVALID_PROPOSAL)
    base_source = _validate_source_ref_fields(value["base_source"])
    _check_ws_path_ownership(base_source, work_ref, INVALID_PROPOSAL)
    if not _is_lower_hex(value["candidate_sha256"], 64):
        _fail(INVALID_PROPOSAL)
    rationale = value["rationale"]
    if not _is_str(rationale):
        _fail(INVALID_PROPOSAL)
    if len(rationale) > MAX_RATIONALE_CHARS or not rationale.strip():
        _fail(INVALID_PROPOSAL)
    evidence = value["evidence"]
    if not isinstance(evidence, list):
        _fail(INVALID_PROPOSAL)
    if len(evidence) > MAX_EVIDENCE_REFS:
        _fail(INVALID_PROPOSAL)
    detached_evidence = []
    for item in evidence:
        detached_evidence.append(_validate_source_ref_fields(item))
    return {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id,
        "work_ref": ref_work_ref,
        "base_adoption": base_adoption,
        "base_source": base_source,
        "candidate_sha256": value["candidate_sha256"],
        "rationale": rationale,
        "evidence": detached_evidence,
    }


def validate_proposal(value, *, work_ref, candidate_bytes):
    """Return a detached validated proposal header for exact candidate bytes.

    ``candidate_bytes`` is the owner-supplied proposed Markdown content, not
    serializer output: it must be exact ``bytes``, decodable as UTF-8, within
    the 1..131072 byte budget, and must hash to ``candidate_sha256``.  The
    header carries no granted/adopted/status/Job/lease/authority field and
    extras are rejected.  ``base_adoption: null`` with an exact recorded
    ``base_source`` never implies acceptance.
    """
    _validate_work_ref(work_ref)
    _require_dict(value, INVALID_PROPOSAL)
    _require_exact_keys(value, PROPOSAL_KEYS, INVALID_PROPOSAL)
    header = _validate_proposal_header(value, work_ref)
    if not isinstance(candidate_bytes, bytes) or isinstance(candidate_bytes, bool):
        _fail(SOURCE_BYTES_MISMATCH)
    try:
        candidate_bytes.decode("utf-8")
    except UnicodeDecodeError:
        _fail(INVALID_PROPOSAL)
    if not 1 <= len(candidate_bytes) <= MAX_CANDIDATE_BYTES:
        _fail(CONTENT_OVER_BUDGET)
    if _sha256_hex(candidate_bytes) != header["candidate_sha256"]:
        _fail(SOURCE_BYTES_MISMATCH)
    return header


def _validate_current(current):
    """Validate the shape of a ``select_current_adoption`` result or ``None``."""
    if current is None:
        return None
    _require_dict(current, INVALID_ADOPTION)
    _require_exact_keys(current, CURRENT_KEYS, INVALID_ADOPTION)
    if not _is_dec_ref_form(current["decision_ref"]):
        _fail(INVALID_ADOPTION)
    _require_dict(current["adoption"], INVALID_ADOPTION)
    _require_exact_keys(current["adoption"], ADOPTION_KEYS, INVALID_ADOPTION)
    current_work_ref = current["adoption"]["work_ref"]
    if not _is_work_ref_form(current_work_ref):
        _fail(INVALID_ADOPTION)
    return {"decision_ref": current["decision_ref"],
            "adoption": validate_adoption(current["adoption"], work_ref=current_work_ref)}


def require_expected_predecessor(adoption, current):
    """Require the candidate adoption's predecessor to match ``current``.

    ``current`` is a :func:`select_current_adoption` result or ``None``.  A
    ``None`` current accepts only a ``None`` predecessor (actual initial
    baseline).  Otherwise the predecessor must equal ``current``'s decision
    ref exactly, else ``STALE_PREDECESSOR``.  The caller still owns the real
    write compare-and-swap and current-source qualification; this pure check
    creates no write.
    """
    _require_dict(adoption, INVALID_ADOPTION)
    _require_exact_keys(adoption, ADOPTION_KEYS, INVALID_ADOPTION)
    candidate_work_ref = adoption["work_ref"]
    if not _is_work_ref_form(candidate_work_ref):
        _fail(INVALID_ADOPTION)
    validated = validate_adoption(adoption, work_ref=candidate_work_ref)
    current = _validate_current(current)
    if current is not None and current["adoption"]["work_ref"] != candidate_work_ref:
        _fail(WORK_REF_MISMATCH)
    expected = None if current is None else current["decision_ref"]
    if validated["predecessor"] != expected:
        _fail(STALE_PREDECESSOR)


def require_proposal_base(proposal, current):
    """Require the proposal header's base to match ``current``.

    With a ``None`` current the proposal must declare ``base_adoption: null``.
    Otherwise the proposal ``base_adoption`` must equal ``current``'s decision
    ref and ``base_source`` must equal ``current``'s adopted source reference
    (all four reference fields), else ``STALE_PREDECESSOR``.  Equality of
    references is not evidence that bodies were read and is never comparison
    output; the caller binds actual bytes separately.
    """
    _require_dict(proposal, INVALID_PROPOSAL)
    _require_exact_keys(proposal, PROPOSAL_KEYS, INVALID_PROPOSAL)
    proposal_work_ref = proposal["work_ref"]
    if not _is_work_ref_form(proposal_work_ref):
        _fail(INVALID_PROPOSAL)
    header = _validate_proposal_header(proposal, proposal_work_ref)
    current = _validate_current(current)
    if current is not None and current["adoption"]["work_ref"] != proposal_work_ref:
        _fail(WORK_REF_MISMATCH)
    if current is None:
        if header["base_adoption"] is not None:
            _fail(STALE_PREDECESSOR)
        return
    if header["base_adoption"] != current["decision_ref"]:
        _fail(STALE_PREDECESSOR)
    if header["base_source"] != current["adoption"]["adopted_source"]:
        _fail(STALE_PREDECESSOR)


def _validate_record_affects(record):
    affects = record.get("affects")
    if not isinstance(affects, list):
        _fail(INVALID_ADOPTION)
    for item in affects:
        if not _is_str(item):
            _fail(INVALID_ADOPTION)
    return affects


def _validate_scoped_record_id(record):
    key = record.get("key")
    if not _is_kebab_key(key):
        _fail(INVALID_ADOPTION)
    return key


def _validate_lineage_refs(record):
    supersedes = record.get("supersedes")
    if supersedes is None:
        supersedes = []
    if not isinstance(supersedes, list):
        _fail(LINEAGE_CONFLICT)
    for item in supersedes:
        if not _is_dec_ref_form(item):
            _fail(LINEAGE_CONFLICT)
    superseded_by = record.get("superseded_by")
    if superseded_by is not None and not _is_dec_ref_form(superseded_by):
        _fail(LINEAGE_CONFLICT)
    return list(supersedes), superseded_by


def select_current_adoption(records, *, work_ref):
    """Select the single current adoption from parsed DEC records.

    ``records`` is a list of up to 128 already-parsed existing DEC dicts; no
    new registry is created and caller records are never mutated.  Records
    without ``project_plan_adoption`` metadata are ignored (legacy records
    stay unaffected).  An adoption record is relevant only when its metadata
    work ref and its ``affects`` list agree about this target; any
    disagreement refuses.  Every scoped chain is validated: each
    predecessor must exist in the scoped graph, occur in its record's
    ``supersedes`` and be pointed back at by the predecessor's
    ``superseded_by``; each non-null ``superseded_by`` must name a scoped
    successor whose predecessor points back.  Self links, cycles, branches,
    competing heads, disconnected components, duplicate scoped keys and
    invisible omitted nodes are rejected rather than resolved.  ``decided_at``
    is never read; no timestamp elects a head.  Returns ``None`` only when
    there are genuinely no scoped adoption records, otherwise a detached
    ``{"decision_ref", "adoption"}`` result for the single valid head.
    """
    _validate_work_ref(work_ref)
    if not isinstance(records, list):
        _fail(INVALID_ADOPTION)
    if len(records) > MAX_RECORDS:
        _fail(INVALID_ADOPTION)
    scoped = {}
    order = []
    for record in records:
        if not isinstance(record, dict):
            _fail(INVALID_ADOPTION)
        if "project_plan_adoption" not in record:
            continue
        affects = _validate_record_affects(record)
        metadata = record["project_plan_adoption"]
        if not isinstance(metadata, dict):
            _fail(INVALID_ADOPTION)
        metadata_work_ref = metadata.get("work_ref")
        if not _is_work_ref_form(metadata_work_ref):
            _fail(INVALID_ADOPTION)
        claimed = metadata_work_ref == work_ref
        in_affects = work_ref in affects
        if claimed != in_affects:
            _fail(LINEAGE_CONFLICT)
        if not claimed:
            continue
        key = _validate_scoped_record_id(record)
        if key in scoped:
            _fail(LINEAGE_CONFLICT)
        validated = validate_adoption(metadata, work_ref=work_ref)
        supersedes, superseded_by = _validate_lineage_refs(record)
        scoped[key] = {
            "adoption": validated,
            "supersedes": supersedes,
            "superseded_by": superseded_by,
        }
        order.append(key)
    _validate_scoped_graph(scoped, order)
    if not order:
        return None
    for key in order:
        if scoped[key]["superseded_by"] is None:
            return {
                "decision_ref": _dec_ref(key),
                "adoption": scoped[key]["adoption"],
            }
    _fail(LINEAGE_CONFLICT)


def _validate_scoped_graph(scoped, order):
    """Validate every scoped chain: links, reciprocity, single head, no cycles."""
    if not order:
        return
    for key in order:
        node = scoped[key]
        predecessor = node["adoption"]["predecessor"]
        if predecessor is None:
            for item in node["supersedes"]:
                if _scoped_key(item) in scoped:
                    _fail(LINEAGE_CONFLICT)
            continue
        predecessor_key = _scoped_key(predecessor)
        if predecessor_key not in scoped:
            _fail(LINEAGE_INCOMPLETE)
        if predecessor not in node["supersedes"]:
            _fail(LINEAGE_CONFLICT)
        for item in node["supersedes"]:
            item_key = _scoped_key(item)
            if item_key in scoped and item != predecessor:
                _fail(LINEAGE_CONFLICT)
        if scoped[predecessor_key]["superseded_by"] != _dec_ref(key):
            _fail(LINEAGE_CONFLICT)
        predecessor_node = scoped[predecessor_key]
        if predecessor_node["adoption"]["predecessor"] == predecessor:
            _fail(LINEAGE_CONFLICT)
    for key in order:
        node = scoped[key]
        superseded_by = node["superseded_by"]
        if superseded_by is None:
            continue
        if superseded_by == _dec_ref(key):
            _fail(LINEAGE_CONFLICT)
        successor_key = _scoped_key(superseded_by)
        if successor_key not in scoped:
            _fail(LINEAGE_INCOMPLETE)
        successor = scoped[successor_key]
        if successor["adoption"]["predecessor"] != _dec_ref(key):
            _fail(LINEAGE_CONFLICT)
    for key in order:
        visited = set()
        current_key = key
        while True:
            if current_key in visited:
                _fail(LINEAGE_CONFLICT)
            visited.add(current_key)
            predecessor = scoped[current_key]["adoption"]["predecessor"]
            if predecessor is None:
                break
            current_key = _scoped_key(predecessor)
    heads = [
        key for key in order if scoped[key]["superseded_by"] is None
    ]
    if len(heads) != 1:
        _fail(LINEAGE_CONFLICT)
    head = heads[0]
    walked = set()
    current_key = head
    while True:
        walked.add(current_key)
        predecessor = scoped[current_key]["adoption"]["predecessor"]
        if predecessor is None:
            break
        current_key = _scoped_key(predecessor)
    if len(walked) != len(order):
        _fail(LINEAGE_CONFLICT)
