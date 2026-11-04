#!/usr/bin/env python3
"""scripts/agentos_project_proposal.py — DRAFT_ONLY project-proposal compiler.

A pure compiler at the AUTHORING edge of the Agent OS knowledge plane.  It takes
one fully-authored project-proposal request and returns the text of a
``agentos/workstreams/WS-<KEY>.md`` record draft as a detached dict.  It reads
nothing, writes nothing, talks to nothing, spawns nothing, and derives nothing
from the clock: the same validated input always compiles to the same bytes.

BOUNDARY — what this module is NOT (and says so in its own output):

* Not a store writer.  ``agentos/workstreams/`` is never touched.  The draft
  exists only in the returned ``content_utf8``; carrying it into the store is a
  separate publication step this module can neither perform nor prove.
* Not a Git client and not an authority.  ``expected_commit`` is an OBLIGATION
  the author pins for that later publisher.  The compiler cannot verify, mint,
  advance or CAS a commit, and its output deliberately says nothing about
  source publication, branches, pull requests or default branches.
* Not a session or lifecycle participant.  A compiled draft carries no
  ``created``/``updated`` (derived elsewhere from git), no ``claim``, no
  ``runtime_ref``, no session/dispatch identity, and it never records that a
  conversation happened.  Status is always ``proposed`` and every wave is
  ``todo``: a proposal has not started, and no output of this compiler may
  claim otherwise.

WHERE THIS MODULE'S LAW ENDS, the canonical checker takes over.  Enum
membership (workstream status, class, blast radius, ambiguity, repos, wave
status), actual program membership, wave dependency dangling/cycle analysis,
and key/filename agreement are decided by ``scripts.agentos.check_workstream``
using the checker's OWN enum sets — imported here, never re-declared.  This
module adds only the compiler-local law the checker cannot know:

* the request envelope (exact keys, exact schema string, strict-ASCII
  ``request_id``, a 40-lowercase-hex ``expected_commit``);
* exact-key closure of the record (a DRAFT carries no runtime, claim, derived
  or ownership fields — an author cannot smuggle them in);
* the proposal-only state rule (``status == 'proposed'``, wave
  ``status == 'todo'``) — strictly narrower than the canonical enums;
* bounded sizes and byte budgets (request canonical JSON <= 16384 bytes,
  returned content <= 32768 UTF-8 bytes);
* character hygiene: non-empty, non-blank, whitespace-clean and control-free
  text where the schema says so (``objective``/``next_action`` may contain LF
  and TAB; nothing else may contain a control character);
* structural depth (a hard nesting cap keeps pathological junk out of the
  error paths and the JSON canonicalisation).

DETERMINISM AND HASHES.  The YAML frontmatter is emitted by
``agentos.yaml.safe_dump(record, sort_keys=False, allow_unicode=True)`` with
one fixed authored key order — the compiler's, not the caller's dict order.
The body is a static module-owned explanation plus exactly one HTML provenance
comment carrying the strict triple ``request_id`` / ``request_sha256`` /
``expected_commit``; caller text (goal, title, objective) never enters the
body.  Hashes never self-reference: ``request_sha256`` is SHA-256 over the
sorted compact JSON of the validated request (``ensure_ascii=False``,
``allow_nan=False``), and ``content_sha256`` is SHA-256 over the returned
content encoded as UTF-8.

DETACHMENT.  The request is treated as frozen: it is never mutated, and the
returned dict shares no mutable structure with it, so mutating the caller's
request after a compile cannot change any earlier result.

PURITY PROOF OBLIGATION.  The module must stay importable and correct under an
I/O ban (``Path.open``/``Path.write_text``/``subprocess``/``socket`` patched to
raise).  ``tests/test_agentos_project_proposal.py`` compiles a full proposal
under exactly that ban, which is the machine-checked form of the sentence
"this compiler never proves a Git write, a store write, or a conversation".

Usage::

    from scripts import agentos_project_proposal

    draft = agentos_project_proposal.compile_proposal(
        request, programs=frozenset(actual_program_keys))
    # draft["content_utf8"] is the full WS-<KEY>.md text; publish it is NOT
    # this module's job and not this module's claim.

``programs`` is keyword-only and required: omitting it is a ``TypeError`` at
the call site, and passing ``None``, an empty set, a non-set, or a set with
non-string/whitespace-padded members is a :class:`ProposalError`.  There is no
default program and no default owner; program membership must be actual.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from scripts import agentos

__all__ = ["ProposalError", "compile_proposal", "OUTPUT_SCHEMA", "REQUEST_SCHEMA"]

REQUEST_SCHEMA = "agentos.project_proposal_request.v1"
OUTPUT_SCHEMA = "agentos.project_proposal.v1"
DRAFT_STATE = "DRAFT_ONLY"

# Exact-key closure.  Anything else in the request or the record is refused —
# in particular every runtime/derived/claim/ownership field the workstream
# schema defines elsewhere (created, updated, claim, owns_paths, runtime_ref,
# wait, p0, ...): a DRAFT compiled here must not be able to carry them.
REQUEST_KEYS = frozenset({"schema", "request_id", "expected_commit", "record"})
RECORD_KEYS = frozenset(
    {
        "key",
        "title",
        "objective",
        "status",
        "program",
        "repos",
        "owner",
        "class",
        "blast_radius",
        "ambiguity",
        "waves",
        "next_action",
    }
)
WAVE_REQUIRED_KEYS = frozenset({"id", "title", "status"})
WAVE_OPTIONAL_KEYS = frozenset({"depends_on"})

# One stable authored key order for the emitted frontmatter — the compiler's,
# never the caller's dict order.
RECORD_KEY_ORDER = (
    "key",
    "title",
    "objective",
    "status",
    "program",
    "repos",
    "owner",
    "class",
    "blast_radius",
    "ambiguity",
    "waves",
    "next_action",
)
WAVE_KEY_ORDER = ("id", "title", "status", "depends_on")

# Mandated input shapes.  fullmatch (never .match): Python's '$' accepts a
# trailing newline, and the canonical KEY_RE's '^...$' would too — the compiler
# keys off fullmatch so 'KEY\n' cannot ride through as UPPER-KEBAB.
REQUEST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")

PROPOSED_STATUS = "proposed"
TODO_WAVE_STATUS = "todo"

MAX_KEY_CHARS = 64
MAX_TITLE_CHARS = 200
MAX_OBJECTIVE_CHARS = 4000
MAX_NEXT_ACTION_CHARS = 1000
MAX_OWNER_CHARS = 200
MAX_PROGRAM_CHARS = 128
MAX_WAVE_ID_CHARS = 64
MAX_WAVE_TITLE_CHARS = 200
MAX_WAVES = 16
MAX_REPOS = 3
MAX_REQUEST_BYTES = 16384
MAX_CONTENT_BYTES = 32768
MAX_STRUCTURE_DEPTH = 8

WORKSTREAM_DIR = "agentos/workstreams"

_YAML_WIDTH = 4096


class ProposalError(ValueError):
    """The compiler refused the request.

    A subclass of ``ValueError`` so callers can catch the plain builtin, with a
    message that names the offending request/record path and the rule that
    fired.  Every refusal is a complete sentence about THIS input; nothing in
    it is advice about retries, stores, or authority.
    """


# ---------------------------------------------------------------- primitives


def _brief(value: object, limit: int = 120) -> str:
    """A bounded repr for error messages (values here are already shallow)."""
    text = repr(value)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


def _require_text(value: object, where: str) -> str:
    if not isinstance(value, str):
        raise ProposalError(f"{where}: expected a string, got {_brief(value)}")
    return value


def _require_visible(value: str, where: str) -> str:
    if not value.strip():
        raise ProposalError(f"{where}: must be a non-empty, non-blank string")
    return value


def _require_no_surrounding_whitespace(value: str, where: str) -> str:
    if value != value.strip():
        raise ProposalError(
            f"{where}: must not start or end with whitespace, got {_brief(value)}"
        )
    return value


def _require_length(value: str, where: str, limit: int) -> str:
    if len(value) > limit:
        raise ProposalError(
            f"{where}: is {len(value)} characters; the limit is {limit}"
        )
    return value


def _has_forbidden_control(value: str, *, multiline: bool) -> bool:
    """True when ``value`` carries a Unicode control character (category Cc).

    ``multiline`` fields (objective, next_action) may carry LF and TAB and
    nothing else from Cc; single-line fields may carry none at all.  NUL, CR,
    ESC, DEL and the C1 range are always forbidden.
    """
    for ch in value:
        if unicodedata.category(ch) != "Cc":
            continue
        if multiline and ch in ("\n", "\t"):
            continue
        return True
    return False


def _require_no_control(value: str, where: str, *, multiline: bool) -> str:
    if _has_forbidden_control(value, multiline=multiline):
        allowed = "LF and TAB only" if multiline else "none"
        raise ProposalError(
            f"{where}: must not contain control characters ({allowed} allowed "
            "for a multiline field)"
        )
    return value


def _reject_deep(value: object, where: str) -> None:
    """Refuse pathological nesting before any repr/canonicalisation sees it.

    Iterative on purpose: a recursive walker over 5000-deep junk is the crash
    this guard exists to prevent.
    """
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_STRUCTURE_DEPTH:
            raise ProposalError(
                f"{where}: nesting deeper than {MAX_STRUCTURE_DEPTH} levels is "
                "refused (structural junk, not a proposal)"
            )
        if isinstance(item, dict):
            for child in item.values():
                stack.append((child, depth + 1))
        elif isinstance(item, (list, tuple)):
            for child in item:
                stack.append((child, depth + 1))


# ------------------------------------------------------------- programs


def _validate_programs(programs: object) -> frozenset:
    """The supplied catalog is the ONLY source of program membership."""
    if not isinstance(programs, (set, frozenset)):
        raise ProposalError(
            "programs: expected a non-empty set of program keys, got "
            f"{_brief(programs)}"
        )
    if not programs:
        raise ProposalError(
            "programs: the supplied catalog is empty; program membership must "
            "be actual and there is no default program"
        )
    for name in programs:
        if not isinstance(name, str):
            raise ProposalError(
                f"programs: catalog keys must be strings, got {_brief(name)}"
            )
        if not name or name != name.strip():
            raise ProposalError(
                "programs: catalog keys must be non-empty and free of "
                f"surrounding whitespace, got {_brief(name)}"
            )
        if _has_forbidden_control(name, multiline=False):
            raise ProposalError(
                f"programs: catalog keys must not contain control characters, "
                f"got {_brief(name)}"
            )
    return frozenset(programs)


# ------------------------------------------------------------- envelope


def _validate_envelope(request: dict) -> tuple:
    """Validate the four-key request envelope; return the scalar triple."""
    if set(request) != REQUEST_KEYS:
        missing = sorted(REQUEST_KEYS - set(request))
        unexpected = sorted(str(name) for name in set(request) - REQUEST_KEYS)
        raise ProposalError(
            "request: exact keys "
            + ", ".join(sorted(REQUEST_KEYS))
            + " are required; missing "
            + repr(missing)
            + "; unexpected "
            + repr(unexpected)
        )
    schema = request["schema"]
    if schema != REQUEST_SCHEMA:
        raise ProposalError(
            f"request.schema: must be {REQUEST_SCHEMA!r}, got {_brief(schema)}"
        )
    request_id = _require_text(request["request_id"], "request.request_id")
    if not REQUEST_ID_RE.fullmatch(request_id):
        raise ProposalError(
            "request.request_id: must be strict ASCII matching "
            "[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}, got " + _brief(request_id)
        )
    expected_commit = _require_text(request["expected_commit"], "request.expected_commit")
    if not COMMIT_RE.fullmatch(expected_commit):
        raise ProposalError(
            "request.expected_commit: must be exactly 40 lowercase hex "
            "characters, got " + _brief(expected_commit)
        )
    return request_id, expected_commit


# ------------------------------------------------------------- record


def _validate_record(record: dict, catalog: frozenset) -> dict:
    """Validate every authored field; return the compiler-ordered record.

    Membership rules stay with the canonical checker's own sets (imported as
    ``agentos.CLASSES`` etc.) — this module never re-declares an enum.
    """
    if set(record) != RECORD_KEYS:
        missing = sorted(RECORD_KEYS - set(record))
        unexpected = sorted(str(name) for name in set(record) - RECORD_KEYS)
        raise ProposalError(
            "record: exact keys "
            + ", ".join(sorted(RECORD_KEYS))
            + " are required; missing "
            + repr(missing)
            + "; unexpected "
            + repr(unexpected)
        )

    # key — canonical KEY_RE, full match, bounded; the path it produces is
    # re-checked below as a traversal backstop before any Path is built.
    key = _require_text(record["key"], "record.key")
    _require_length(key, "record.key", MAX_KEY_CHARS)
    if not agentos.KEY_RE.fullmatch(key):
        raise ProposalError(
            "record.key: must be UPPER-KEBAB per the canonical KEY_RE "
            "(full match), got " + _brief(key)
        )

    title = _require_text(record["title"], "record.title")
    _require_visible(title, "record.title")
    _require_length(title, "record.title", MAX_TITLE_CHARS)
    _require_no_control(title, "record.title", multiline=False)

    objective = _require_text(record["objective"], "record.objective")
    _require_visible(objective, "record.objective")
    _require_length(objective, "record.objective", MAX_OBJECTIVE_CHARS)
    _require_no_control(objective, "record.objective", multiline=True)

    status = _require_text(record["status"], "record.status")
    if status != PROPOSED_STATUS or status not in agentos.WORKSTREAM_STATUS:
        raise ProposalError(
            "record.status: this compiler emits proposals only; status must be "
            f"{PROPOSED_STATUS!r} (canonical workstream statuses: "
            + ", ".join(sorted(agentos.WORKSTREAM_STATUS))
            + "), got "
            + _brief(status)
        )

    program = _require_text(record["program"], "record.program")
    _require_no_surrounding_whitespace(program, "record.program")
    _require_visible(program, "record.program")
    _require_length(program, "record.program", MAX_PROGRAM_CHARS)
    _require_no_control(program, "record.program", multiline=False)
    if program not in catalog:
        raise ProposalError(
            f"record.program: {program!r} is not in the supplied program "
            "catalog; membership must be actual — no default program is assumed"
        )

    repos = record["repos"]
    if not isinstance(repos, list):
        raise ProposalError(
            f"record.repos: expected a list of 1..{MAX_REPOS} canonical repo "
            f"keys, got {_brief(repos)}"
        )
    if not 1 <= len(repos) <= MAX_REPOS:
        raise ProposalError(
            f"record.repos: must list 1..{MAX_REPOS} repos, got {len(repos)}"
        )
    seen_repos: list = []
    for index, repo in enumerate(repos):
        where = f"record.repos[{index}]"
        repo = _require_text(repo, where)
        if repo not in agentos.REPOS:
            raise ProposalError(
                f"{where}: {repo!r} is not a canonical repo (allowed: "
                + ", ".join(sorted(agentos.REPOS))
                + ")"
            )
        if repo in seen_repos:
            raise ProposalError(f"{where}: duplicate repo {repo!r}")
        seen_repos.append(repo)

    owner = _require_text(record["owner"], "record.owner")
    _require_no_surrounding_whitespace(owner, "record.owner")
    _require_visible(owner, "record.owner")
    _require_length(owner, "record.owner", MAX_OWNER_CHARS)
    _require_no_control(owner, "record.owner", multiline=False)

    checked: dict = {}
    for field, allowed in (
        ("class", agentos.CLASSES),
        ("blast_radius", agentos.BLAST),
        ("ambiguity", agentos.AMBIGUITY),
    ):
        value = _require_text(record[field], f"record.{field}")
        if value not in allowed:
            raise ProposalError(
                f"record.{field}: {value!r} is not canonical (allowed: "
                + ", ".join(sorted(allowed))
                + ")"
            )
        checked[field] = value

    next_action = _require_text(record["next_action"], "record.next_action")
    _require_visible(next_action, "record.next_action")
    _require_length(next_action, "record.next_action", MAX_NEXT_ACTION_CHARS)
    _require_no_control(next_action, "record.next_action", multiline=True)

    waves = _compile_waves(record["waves"])
    return {
        "key": key,
        "title": title,
        "objective": objective,
        "status": status,
        "program": program,
        "repos": list(repos),
        "owner": owner,
        "class": checked["class"],
        "blast_radius": checked["blast_radius"],
        "ambiguity": checked["ambiguity"],
        "waves": waves,
        "next_action": next_action,
    }


def _compile_waves(waves: object) -> list:
    """Validate 1..16 proposal waves; return rebuilt, detached wave dicts.

    Dependency dangling/cycle analysis and duplicate-id detection stay with the
    canonical checker.  ``depends_on`` entries are type-checked HERE, because
    the canonical checker silently drops non-string entries — dropping an edge
    is exactly the failure a proposal compiler must not inherit.
    """
    if not isinstance(waves, list):
        raise ProposalError(f"record.waves: expected a list of waves, got {_brief(waves)}")
    if not 1 <= len(waves) <= MAX_WAVES:
        raise ProposalError(
            f"record.waves: a proposal carries 1..{MAX_WAVES} waves, got {len(waves)}"
        )
    out: list = []
    for index, wave in enumerate(waves):
        where = f"record.waves[{index}]"
        if not isinstance(wave, dict):
            raise ProposalError(f"{where}: expected a mapping, got {_brief(wave)}")
        keys = set(wave)
        if not WAVE_REQUIRED_KEYS <= keys or not keys <= (
            WAVE_REQUIRED_KEYS | WAVE_OPTIONAL_KEYS
        ):
            raise ProposalError(
                f"{where}: exact keys id,title,status plus optional depends_on; "
                "got " + repr(sorted(str(name) for name in keys))
            )
        wave_id = _require_text(wave["id"], f"{where}.id")
        _require_no_surrounding_whitespace(wave_id, f"{where}.id")
        _require_visible(wave_id, f"{where}.id")
        _require_length(wave_id, f"{where}.id", MAX_WAVE_ID_CHARS)
        _require_no_control(wave_id, f"{where}.id", multiline=False)
        wave_title = _require_text(wave["title"], f"{where}.title")
        _require_visible(wave_title, f"{where}.title")
        _require_length(wave_title, f"{where}.title", MAX_WAVE_TITLE_CHARS)
        _require_no_control(wave_title, f"{where}.title", multiline=False)
        wave_status = _require_text(wave["status"], f"{where}.status")
        if wave_status != TODO_WAVE_STATUS or wave_status not in agentos.WAVE_STATUS:
            raise ProposalError(
                f"{where}.status: a proposal compiles only with todo waves "
                f"(canonical wave statuses: "
                + ", ".join(sorted(agentos.WAVE_STATUS))
                + "), got "
                + _brief(wave_status)
            )
        rebuilt: dict = {"id": wave_id, "title": wave_title, "status": wave_status}
        if "depends_on" in wave:
            deps = wave["depends_on"]
            if not isinstance(deps, list):
                raise ProposalError(
                    f"{where}.depends_on: expected a list of wave ids, got "
                    + _brief(deps)
                )
            checked_deps = []
            for dep_index, dep in enumerate(deps):
                # Type-checked here: the canonical checker silently drops a
                # non-string entry, which would silently lose the edge.
                dep = _require_text(dep, f"{where}.depends_on[{dep_index}]")
                checked_deps.append(dep)
            rebuilt["depends_on"] = checked_deps
        out.append(rebuilt)
    return out


# ------------------------------------------------------------- rendering


_BODY_EXPLANATION = """\
## What this file is

A DRAFT_ONLY workstream record compiled from an authored project-proposal
request. Compilation happened entirely in memory: no store path was read or
written, no Git operation ran, and no authority was granted by producing this
text. The draft reaches the store only if a separate publication step — which
this compiler can neither perform nor prove — carries it into
`agentos/workstreams/` under the commit the request pinned as
`expected_commit`. That commit value is an obligation recorded for that later
publisher, not a fact this file asserts.

## What this file does not say

It carries no `created`/`updated` field (those are derived from git history by
the store tooling, never authored), no `claim`, no `runtime_ref`, and no
session or conversation identity. Status is `proposed` and every wave is
`todo`: nothing here asserts that the work started, merged, shipped, or was
reviewed.

## How to read the frontmatter

The YAML block above is the whole authored record: exactly the twelve
workstream fields, in the compiler's fixed key order, serialized with
`yaml.safe_dump` so caller text (including YAML-looking text, CJK, LF and TAB)
survives byte-exact through `FRONTMATTER_RE` -> `yaml.safe_load`. Membership
rules inside it were checked by the canonical `scripts.agentos` checker, not
re-declared here.
"""


def _provenance_comment(request_id: str, request_sha256: str, expected_commit: str) -> str:
    """The single HTML comment allowed in the body, with the strict triple.

    Every interpolated value is charset-bounded before it gets here (request id
    is strict ASCII, the two digests are lowercase hex), so the comment can
    carry no markup and no newline beyond the ones written literally below.
    """
    return (
        "<!--\n"
        "agentos-project-proposal provenance (DRAFT_ONLY):\n"
        "request_id: " + request_id + "\n"
        "request_sha256: " + request_sha256 + "\n"
        "expected_commit: " + expected_commit + "\n"
        "-->\n"
    )


# ------------------------------------------------------------- API


def compile_proposal(request: object, *, programs: set) -> dict:
    """Compile one authored project-proposal request into a DRAFT_ONLY draft.

    Returns a detached dict with exactly the keys of
    ``agentos.project_proposal.v1``.  Raises :class:`ProposalError` for any
    refused input.  Never mutates ``request`` or ``programs``; reads no file,
    clock, process or socket; performs no Git effect.  The keyword argument
    ``programs`` is required and fail-closed: omitting it raises ``TypeError``
    at the call site, and anything but a non-empty set of clean program-key
    strings raises :class:`ProposalError`.
    """
    catalog = _validate_programs(programs)
    _reject_deep(request, "request")
    if not isinstance(request, dict):
        raise ProposalError(f"request: expected a mapping, got {_brief(request)}")

    request_id, expected_commit = _validate_envelope(request)
    record = request["record"]
    if not isinstance(record, dict):
        raise ProposalError(f"request.record: expected a mapping, got {_brief(record)}")

    compiled = _validate_record(record, catalog)
    key = compiled["key"]

    # The compiled record is rebuilt (never the caller's objects), so the hash
    # below covers the validated request and nothing the caller can mutate.
    snapshot = {
        "schema": REQUEST_SCHEMA,
        "request_id": request_id,
        "expected_commit": expected_commit,
        "record": compiled,
    }
    canonical_request = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(canonical_request) > MAX_REQUEST_BYTES:
        raise ProposalError(
            f"request: canonical JSON is {len(canonical_request)} bytes; the "
            f"budget is {MAX_REQUEST_BYTES}"
        )
    request_sha256 = hashlib.sha256(canonical_request).hexdigest()

    # Traversal backstop: KEY_RE already excludes separators, so this is the
    # recorded invariant, not the only line of defence — the relative path this
    # compiler builds must be exactly the file the checker expects.
    rel_path = WORKSTREAM_DIR + "/WS-" + key + ".md"
    work_path = Path(rel_path)
    expected_name = "WS-" + key + ".md"
    if work_path.is_absolute() or str(work_path) != rel_path or work_path.name != expected_name:
        raise ProposalError(
            "record.key: would not stay inside " + WORKSTREAM_DIR + " as " + expected_name
        )

    # The canonical join.  Hard problems reject the draft; the checker owns
    # enum membership, program membership, dependency dangling/cycles,
    # duplicate wave ids and filename agreement.
    problems = agentos.check_workstream(compiled, work_path, set(catalog))
    hard = [problem for problem in problems if problem.hard]
    if hard:
        detail = "; ".join(
            "[" + problem.rule + "] " + problem.message for problem in hard
        )
        raise ProposalError(
            "canonical check_workstream rejected this proposal: " + detail
        )

    frontmatter = agentos.yaml.safe_dump(
        {name: compiled[name] for name in RECORD_KEY_ORDER},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=_YAML_WIDTH,
    )
    if (
        not frontmatter.endswith("\n")
        or frontmatter.startswith("---")
        or "\n---\n" in frontmatter
    ):  # pragma: no cover - invariant guard over the serialiser
        raise ProposalError(
            "internal: safe_dump produced a payload the frontmatter fence "
            "cannot safely wrap"
        )
    content = (
        "---\n" + frontmatter + "---\n\n" + _BODY_EXPLANATION + "\n"
        + _provenance_comment(request_id, request_sha256, expected_commit)
    )
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_CONTENT_BYTES:
        raise ProposalError(
            f"compiled content is {len(content_bytes)} bytes; the budget is "
            f"{MAX_CONTENT_BYTES}"
        )

    return {
        "schema": OUTPUT_SCHEMA,
        "state": DRAFT_STATE,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "expected_commit": expected_commit,
        "work_ref": "WS:" + key,
        "path": rel_path,
        "content_utf8": content,
        "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
    }
