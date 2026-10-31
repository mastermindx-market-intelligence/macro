"""Single validation chokepoint for news-impact payloads (program upgrade 1).

Implements masterplan sections 3.5 (source text is data, never tool
authority), 5 (corrections rule: a corrected fact must name what it
supersedes), 12 (Phase 1 exit: full rejection accounting) and 14 (upgrade 1:
one validator both the CI job and every later lane call), under Phase 0
freeze decision D17/G5 (injection not-patterns on free strings;
quarantine_note.v1 lives OUTSIDE the publishable templates, so this
validator dispatches only over the three event templates) and seat rulings
R1/R2 (display projection is display-only) and R4 (unknown locator keys are
rejected, never stripped).  The contract itself is frozen (sha256 prefix
3edc7139) and is never mutated here.

Lane B5_semantic (Wave 3, seat Fable 0e739467) adds the semantic layer
S1-S13 and the strict raw-text loader so every fixture of the Wave-2 C1
hostile corpus (33 one-mutation fixtures) reproduces its seat-ratified
verdict without changing any verdict the frozen case files pin (masterplan
section 14 upgrade 1; seat ruling R5 of 2026-10-12 binding the forbidden
vocabulary to identifier-form tokens and provenance identifiers, never to
plain-language words inside verbatim quotes — those are source text under
section 3.5, defended by span replay, not by a word list).  Every issue
still carries exactly one code from the closed REASON_CODES; no new code
was added.  Deterministic by construction: no clock reads, no randomness,
no network, no module-level I/O; ``as_of``-style time never enters
validation.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import date as _date, datetime as _datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable, Iterable

from jsonschema import validators as _jsv

CONTRACT_SHA256_PREFIX = "3edc7139"
CONTRACT_RELPATH = Path("contracts") / "news_impact" / "news_impact_event.v1.schema.json"

SCHEMA_VIOLATION = "schema_violation"
LOCATOR_KEY_NOT_IN_CONTRACT = "locator_key_not_in_contract"
FORBIDDEN_VOCABULARY = "forbidden_vocabulary"
INJECTION_PATTERN = "injection_pattern"
SUPERSEDES_REQUIRED = "supersedes_required"

REASON_CODES = (
    SCHEMA_VIOLATION,
    LOCATOR_KEY_NOT_IN_CONTRACT,
    FORBIDDEN_VOCABULARY,
    INJECTION_PATTERN,
    SUPERSEDES_REQUIRED,
)


class ContractMismatch(Exception):
    """The contract file does not carry the frozen Phase 0 sha256 prefix."""


@dataclass(frozen=True)
class ValidationIssue:
    """One attributable rejection reason at a JSON pointer of the payload."""

    code: str
    path: str  # JSON pointer of the offending node, "" for root
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Verdict plus deduplicated, sorted issues for one payload."""

    ok: bool
    issues: tuple[ValidationIssue, ...]
    fact_id: str | None


class StrictJsonError(ValueError):
    """Raw text that strict loading rejects: ambiguous or non-finite JSON.

    ``code`` is one of :data:`REASON_CODES` (``injection_pattern`` for a
    duplicate object key — a last-wins swap silently changes fact identity,
    which is an integrity attack on the byte stream, not a shape fault;
    ``schema_violation`` for a bare NaN/Infinity/-Infinity token, rule S1).
    ``path`` is the JSON pointer of the object holding the duplicate key,
    or ``""`` when the parser position is not exposed (parse-time
    constants).  Subclasses :class:`ValueError` so existing ``except``
    clauses keep working.
    """

    code: str
    path: str

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.path = path


# --------------------------------------------------------------------- contract

def load_contract(path: str | Path | None = None) -> dict:
    """Load the frozen contract, verifying its sha256 prefix.

    Default path is ``<repo>/contracts/news_impact/news_impact_event.v1.schema.json``
    resolved relative to this module (``Path(__file__).resolve().parents[2]``).
    Raises :class:`ContractMismatch` naming both the expected and the found
    prefix when the file bytes do not start with ``3edc7139``.
    """
    p = Path(path) if path is not None else Path(__file__).resolve().parents[2] / CONTRACT_RELPATH
    data = p.read_bytes()
    digest = sha256(data).hexdigest()
    if not digest.startswith(CONTRACT_SHA256_PREFIX):
        raise ContractMismatch(
            f"contract {p} sha256 starts with {digest[:len(CONTRACT_SHA256_PREFIX)]}, "
            f"expected frozen prefix {CONTRACT_SHA256_PREFIX}")
    return json.loads(data.decode("utf-8"))


def _resolve_ref(contract: dict, ref: str) -> dict | None:
    node = contract
    for part in ref.lstrip("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node if isinstance(node, dict) else None


# ------------------------------------------------------------------ dispatching

@dataclass
class _Context:
    """Prepared validators for one loaded contract (no shared module state)."""

    contract: dict
    template_names: tuple[str, ...]  # sorted, only branches with a nameable const discriminator
    discriminator_missing: bool  # some oneOf branch carries no such discriminator
    cache: dict  # template name (or "whole") -> validator, built lazily
    # Semantic-layer indices over the SAME frozen contract (rule S6/S7/S8):
    text_safe_props: frozenset = frozenset()      # property names the contract types via text_safe
    calendar_props: dict = field(default_factory=dict)  # property name -> 'date'|'date-time'|'either'
    role_marker_patterns: tuple = ()              # compiled role-marker branches of text_safe

    @classmethod
    def build(cls, contract: dict) -> "_Context":
        names = []
        missing = False
        for branch in contract.get("oneOf", []):
            node, name = branch, None
            if isinstance(branch, dict) and "$ref" in branch:
                ref = branch["$ref"]
                if ref.startswith("#/$defs/"):
                    name = ref.split("/")[-1]
                node = _resolve_ref(contract, ref)
            disc = None
            if isinstance(node, dict):
                disc = node.get("properties", {}).get("schema", {}).get("const")
            if isinstance(disc, str) and name is not None:
                names.append(name)
            else:
                missing = True  # a branch without a nameable const discriminator
        ctx = cls(contract=contract, template_names=tuple(sorted(set(names))),
                  discriminator_missing=missing, cache={})
        ctx._index_text_safe_props()
        ctx._index_calendar_props()
        ctx._index_role_marker_patterns()
        return ctx

    # -- semantic-layer indices (pure walks over the frozen contract) ------

    def _iter_property_nodes(self):
        """Yield ``(name, node)`` for every ``properties`` entry anywhere in the contract."""
        def walk(node, trail):
            if not isinstance(node, dict) or id(node) in trail:
                return
            trail = trail | {id(node)}
            props = node.get("properties")
            if isinstance(props, dict):
                for name, sub in props.items():
                    if isinstance(name, str) and isinstance(sub, dict):
                        yield name, sub
            for value in node.values():
                if isinstance(value, dict):
                    yield from walk(value, trail)
                elif isinstance(value, list):
                    for branch in value:
                        if isinstance(branch, dict):
                            yield from walk(branch, trail)
        yield from walk(self.contract, frozenset())

    def _admits_text_safe(self, node, trail=frozenset()) -> bool:
        """True when ``node`` (through $ref/oneOf/anyOf) reaches the text_safe def."""
        if not isinstance(node, dict):
            return False
        if "$ref" in node:
            ref = node["$ref"]
            if ref in trail:
                return False
            target = _resolve_ref(self.contract, ref)
            if target is None:
                return False
            if target is self.contract.get("$defs", {}).get("text_safe"):
                return True
            return self._admits_text_safe(target, trail | {ref})
        for key in ("oneOf", "anyOf"):
            for branch in node.get(key, []) or []:
                if self._admits_text_safe(branch, trail):
                    return True
        return False

    def _index_text_safe_props(self) -> None:
        self.text_safe_props = frozenset(
            name for name, node in self._iter_property_nodes()
            if self._admits_text_safe(node))

    def _index_calendar_props(self) -> None:
        merged: dict[str, str] = {}
        for name, node in self._iter_property_nodes():
            kind = self._calendar_kind(node)
            if kind is None:
                continue
            merged[name] = kind if name not in merged else _widen_calendar(merged[name], kind)
        self.calendar_props = merged

    def _calendar_kind(self, node, trail=frozenset()) -> str | None:
        """'date', 'date-time' or 'either' when the contract types the node as calendar.

        The contract declares calendar lexical spaces two ways: the JSON
        Schema ``format`` keyword (envelope observed_at / source_available_at)
        or an explicit ISO-8601 ``pattern`` (baseline.timestamp,
        fiscal_period.calendar_end).  Both are schema-node declarations of
        the same duty, so both feed rule S6.
        """
        if not isinstance(node, dict):
            return None
        kinds = set()
        fmt = node.get("format")
        if fmt == "date":
            kinds.add("date")
        elif fmt == "date-time":
            kinds.add("date-time")
        pattern = node.get("pattern")
        if isinstance(pattern, str):
            kinds |= _iso_pattern_kinds(pattern)
        if "$ref" in node and node["$ref"] not in trail:
            ref = node["$ref"]
            target = _resolve_ref(self.contract, ref)
            if target is not None:
                kind = self._calendar_kind(target, trail | {ref})
                if kind is not None:
                    kinds.add(kind)
        for key in ("oneOf", "anyOf"):
            for branch in node.get(key, []) or []:
                kind = self._calendar_kind(branch, trail)
                if kind is not None:
                    kinds.add(kind)
        if len(kinds) == 1:
            return kinds.pop()
        if kinds:
            return "either"
        return None

    def _index_role_marker_patterns(self) -> None:
        """The text_safe branches that mark LLM role markers (rule S8).

        A branch is a role-marker branch when its pattern names one of the
        chat roles AND requires a colon after it — the anchored
        ``(system|assistant|developer|user|tool|function)\\s*[:\\uff1a]``
        branch and the homoglyph ``[s\\u0455]ystem\\s*[:\\uff1a]`` branch.
        Heading markers (``### system``) and URL schemes carry no colon
        binding and are excluded.
        """
        text_safe = self.contract.get("$defs", {}).get("text_safe", {})
        patterns = []
        for branch in text_safe.get("not", {}).get("anyOf", []) or []:
            pattern = branch.get("pattern") if isinstance(branch, dict) else None
            if not isinstance(pattern, str):
                continue
            if not _ROLE_WORD_RE.search(pattern.replace("[", "").replace("]", "")):
                continue
            if "[:：]" not in pattern:
                continue
            patterns.append(re.compile(pattern))
        self.role_marker_patterns = tuple(patterns)

    def template_validator(self, name: str):
        if name not in self.cache:
            doc = {k: v for k, v in self.contract.items() if k != "oneOf"}
            doc["$ref"] = f"#/$defs/{name}"
            cls = _jsv.validator_for(self.contract)  # honours the declared $schema
            self.cache[name] = cls(doc)
        return self.cache[name]

    def whole_validator(self):
        if "whole" not in self.cache:
            cls = _jsv.validator_for(self.contract)
            self.cache["whole"] = cls(self.contract)
        return self.cache["whole"]

    def dispatch(self, payload: dict) -> str | None:
        """Template name whose ``schema`` const the payload carries, if any."""
        value = payload.get("schema")
        if not isinstance(value, str):
            return None
        for name in self.template_names:
            node = _resolve_ref(self.contract, f"#/$defs/{name}")
            if isinstance(node, dict) and \
                    node.get("properties", {}).get("schema", {}).get("const") == value:
                return name
        return None


_ISO_DAY_PREFIX = "^[0-9]{4}-[0-9]{2}-[0-9]{2}"
# chat-role words, including the Cyrillic homoglyph spellings text_safe itself
# branches on (ѕ U+0455, а U+0430)
_ROLE_WORD_RE = re.compile(
    "system|assistant|developer|user|tool|function|ѕystem|аssistant")


def _iso_pattern_kinds(pattern: str) -> set:
    """Calendar kinds declared by an ISO-anchored ``pattern`` string."""
    if not pattern.startswith(_ISO_DAY_PREFIX):
        return set()
    rest = pattern[len(_ISO_DAY_PREFIX):]
    if rest == "$":
        return {"date"}
    if rest.startswith("(T") and rest.endswith(")?$"):
        return {"date", "date-time"}  # date or date-time, both admitted
    if rest.startswith("T"):
        return {"date-time"}
    return set()


def _widen_calendar(a: str, b: str) -> str:
    if a == b:
        return a
    return "either"


# --------------------------------------------------------------- classification

_LOCATOR_KINDS = frozenset({"text_span", "table_cell", "slide_region"})
_ADDPROPS_VALIDATORS = frozenset({"additionalProperties", "unevaluatedProperties"})

_FORBIDDEN_WORDS = ("confidence", "probability", "likelihood", "score",
                    "price_target", "target_price", "fair_value",
                    "valuation_target", "rating_score")
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATOR_RUN = re.compile(r"[-_.\s]+")


def _normalize_name(name: str) -> str:
    """lower-case, camelCase-split, hyphen/space/underscore/dot-stripped form."""
    return _SEPARATOR_RUN.sub("", _CAMEL_BOUNDARY.sub("_", name).lower())


_FORBIDDEN_NORMALIZED = frozenset(_normalize_name(w) for w in _FORBIDDEN_WORDS)

# R5(b): the vocabulary binds identifier-form tokens (snake_case / camelCase
# joins) inside ANY string value — never plain-language words in a quote.
_VOCAB_JOINED_FORMS = ("price_target", "target_price", "fair_value",
                       "valuation_target", "rating_score", "confidence_score",
                       "contagion_tag")


def _camel_form(word: str) -> str:
    parts = word.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


_JOINED_VOCAB_RE = re.compile(
    "(?i)(?<![a-z0-9_])(" + "|".join(sorted(
        set(list(_VOCAB_JOINED_FORMS) + [_camel_form(w) for w in _VOCAB_JOINED_FORMS])))
    + ")(?![a-z0-9_])")

# R5(c): provenance identifiers.  llm / gpt / synthetic tokens (or the pair
# llm+generated) inside an identifier/profile field name LLM origination.
_PROVENANCE_TOKENS = frozenset({"llm", "gpt", "synthetic"})
_IDENTIFIER_SUFFIXES = ("_id", "_profile")

# S7: URI schemes text_safe does not blocklist.  Word boundary before the
# scheme; the colon must immediately follow the scheme name.
_SCHEME_RE = re.compile(r"(?i)(?<![0-9a-z_])(?:data|blob|vbscript):")

_ORDERED_BYTE_SUFFIXES = (("_start_byte", "_end_byte"), ("_start_char", "_end_char"))


def _escape(token) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def _pointer(keys) -> str:
    return "".join("/" + _escape(k) for k in keys)


def _node_at(payload, keys):
    node = payload
    for k in keys:
        try:
            node = node[k]
        except (TypeError, KeyError, IndexError):
            return None
    return node


def _is_locator_context(payload, keys) -> bool:
    """True when the node at ``keys`` is a locator_* object (ruling R4)."""
    if keys and isinstance(keys[-1], str) and keys[-1] == "locator":
        return True
    node = _node_at(payload, keys)
    return isinstance(node, dict) and node.get("kind") in _LOCATOR_KINDS


def _err_sortkey(err) -> tuple:
    """Deterministic ordering for jsonschema errors and their sub-errors."""
    return (_pointer(err.absolute_path), str(getattr(err, "validator", "") or ""),
            str(err.message))


def _branch_leaves(branch: dict, instance, ctx: "_Context") -> list:
    """Validate ``instance`` against one oneOf/anyOf branch; return its leaves."""
    doc = {"$defs": ctx.contract["$defs"]}
    doc.update(branch)
    sub = _jsv.validator_for(ctx.contract)(doc)
    leaves = []
    for err in sub.iter_errors(instance):
        leaves.extend(_flatten(err, ctx))
    return leaves


def _flatten(error, ctx: "_Context") -> list:
    """Descend oneOf/anyOf so issues point at the real node.

    jsonschema buries branch errors mixed together in ``error.context``;
    instead each branch is re-validated separately and the best-matching
    branch is kept: fewest leaves, then deepest leaf, then a stable
    path/validator/message tie-break.  Returns ``(path_tuple, error)`` pairs
    whose paths are rebased to the payload root.  ``not`` and leaf
    validators carry no branches and return as-is.  A oneOf error where no
    branch fails (an over-match) keeps the original error.
    """
    branches = None
    if getattr(error, "validator", None) in ("oneOf", "anyOf"):
        value = getattr(error, "validator_value", None)
        if isinstance(value, list) and value and \
                all(isinstance(b, dict) for b in value):
            branches = value
    if branches is None:
        return [(tuple(error.absolute_path), error)]

    candidates = [leaves for leaves in
                  (_branch_leaves(branch, error.instance, ctx) for branch in branches)
                  if leaves]
    if not candidates:
        return [(tuple(error.absolute_path), error)]

    def rank(leaves: list) -> tuple:
        depth = max(len(path) for path, _ in leaves)
        return (len(leaves), -depth, _err_sortkey(leaves[0][1]))

    best = min(candidates, key=rank)
    base = tuple(error.absolute_path)
    return [(base + path, leaf) for path, leaf in best]


def _schema_issues(payload: dict, ctx: _Context) -> list[ValidationIssue]:
    """Run jsonschema with branch dispatch; classify every error's reason code."""
    template = None if ctx.discriminator_missing or not isinstance(payload, dict) \
        else ctx.dispatch(payload)
    if ctx.discriminator_missing:
        validator = ctx.whole_validator()
    elif template is None:
        why = "payload is not a JSON object"
        path = ""
        if isinstance(payload, dict):
            value = payload.get("schema")
            why = ("schema discriminator is missing"
                   if value is None else
                   f"no template branch matches schema discriminator {value!r}")
            path = "/schema"
        return [ValidationIssue(SCHEMA_VIOLATION, path, why)]
    else:
        validator = ctx.template_validator(template)

    issues = []
    for err in validator.iter_errors(payload):
        for path_keys, leaf in _flatten(err, ctx):
            path = _pointer(path_keys)
            validator_name = getattr(leaf, "validator", None)
            if validator_name in _ADDPROPS_VALIDATORS and \
                    _is_locator_context(payload, list(path_keys)):
                code = LOCATOR_KEY_NOT_IN_CONTRACT
                message = f"locator key not in contract (ruling R4): {leaf.message}"
            elif validator_name == "not":
                code = INJECTION_PATTERN
                message = f"text_safe not-clause failed: {leaf.message}"
            else:
                code = SCHEMA_VIOLATION
                message = leaf.message
            issues.append(ValidationIssue(code, path, message))
    return issues


def _forbidden_vocabulary_issues(payload) -> list[ValidationIssue]:
    """Rule (b): banned property names anywhere, even where the schema also rejects."""
    issues = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{path}/{_escape(key)}"
                if isinstance(key, str) and _normalize_name(key) in _FORBIDDEN_NORMALIZED:
                    issues.append(ValidationIssue(
                        FORBIDDEN_VOCABULARY, child,
                        f"forbidden vocabulary in property name: {key!r}"))
                walk(value, child)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}/{i}")

    walk(payload, "")
    return issues


def _supersedes_issues(payload) -> list[ValidationIssue]:
    """Rule (d): novelty == corrected_fact demands a non-null supersedes_fact_id."""
    if not isinstance(payload, dict) or payload.get("novelty") != "corrected_fact":
        return []
    if payload.get("supersedes_fact_id") is None:
        return [ValidationIssue(
            SUPERSEDES_REQUIRED, "/supersedes_fact_id",
            "novelty == 'corrected_fact' requires a non-null supersedes_fact_id")]
    return []


def _merge(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    """Apply reclassification precedence before deduplication.

    Rule (d) reclassifies the failure itself: when the corrections rule
    fires, the schema errors it subsumes (the null-typed supersedes node, or
    the root-required error naming it) are replaced by the single
    supersedes_required issue instead of doubling up.
    """
    if any(i.code == SUPERSEDES_REQUIRED for i in issues):
        return [i for i in issues if not (
            i.code == SCHEMA_VIOLATION and (
                i.path == "/supersedes_fact_id"
                or (i.path == "" and "supersedes_fact_id" in i.message)))]
    return issues


def _finalize(issues: list[ValidationIssue], payload) -> ValidationReport:
    unique = sorted(set(issues), key=lambda i: (i.path, i.code, i.message))
    fact_id = None
    if isinstance(payload, dict) and isinstance(payload.get("fact_id"), str):
        fact_id = payload["fact_id"]
    return ValidationReport(ok=not unique, issues=tuple(unique), fact_id=fact_id)


# ------------------------------------------------------------ semantic layer S1+

def _iter_objects(node, keys=()):
    """Yield ``(obj, keys)`` for every JSON object in the payload, root first."""
    if isinstance(node, dict):
        yield node, keys
        for key, value in node.items():
            yield from _iter_objects(value, list(keys) + [key])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_objects(item, list(keys) + [i])


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _parse_iso_datetime(text: str) -> _datetime | None:
    """datetime.datetime.fromisoformat after the trailing-Z replacement (S6)."""
    candidate = text[:-1] + "+00:00" if isinstance(text, str) and text.endswith("Z") else text
    if not isinstance(candidate, str):
        return None
    try:
        return _datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _calendar_ok(value: str, kind: str) -> bool:
    """True when ``value`` is a real calendar value of the declared kind (S6)."""
    if kind == "date":
        try:
            _date.fromisoformat(value)
            return True
        except ValueError:
            return False
    if _parse_iso_datetime(value) is not None:
        return True
    if kind == "either":
        try:
            _date.fromisoformat(value)
            return True
        except ValueError:
            return False
    return False


def _s1_non_finite_numbers(payload, ctx: _Context) -> list[ValidationIssue]:
    """S1: any NaN / +/-Infinity float anywhere -> schema_violation at that node."""
    issues = []
    for obj, keys in _iter_objects(payload):
        for key, value in obj.items():
            if isinstance(value, float) and not math.isfinite(value):
                issues.append(ValidationIssue(
                    SCHEMA_VIOLATION, _pointer(list(keys) + [key]),
                    f"non-finite number {value!r} is not a JSON number (rule S1)"))
    return issues


def _s2_ordered_pairs(payload, ctx: _Context) -> list[ValidationIssue]:
    """S2: a *_start_byte/_end_byte (or *_start_char/_end_char) pair with start > end."""
    issues = []
    for obj, keys in _iter_objects(payload):
        for start_suffix, end_suffix in _ORDERED_BYTE_SUFFIXES:
            for key in sorted(obj):
                if not (isinstance(key, str) and key.endswith(start_suffix)):
                    continue
                end_key = key[:key.rfind(start_suffix)] + end_suffix
                start_value, end_value = obj.get(key), obj.get(end_key)
                if _is_number(start_value) and _is_number(end_value) and start_value > end_value:
                    issues.append(ValidationIssue(
                        SCHEMA_VIOLATION, _pointer(list(keys) + [end_key]),
                        f"{key} {start_value} exceeds {end_key} {end_value} (rule S2)"))
    return issues


def _s3_span_within_segment(payload, ctx: _Context) -> list[ValidationIssue]:
    """S3: a source-span receipt whose span_end_byte exceeds segment_bytes."""
    issues = []
    for obj, keys in _iter_objects(payload):
        end_value, segment_value = obj.get("span_end_byte"), obj.get("segment_bytes")
        if _is_number(end_value) and _is_number(segment_value) and end_value > segment_value:
            issues.append(ValidationIssue(
                SCHEMA_VIOLATION, _pointer(list(keys) + ["span_end_byte"]),
                f"span_end_byte {end_value} exceeds segment_bytes {segment_value} (rule S3)"))
    return issues


def _s4_no_self_supersession(payload, ctx: _Context) -> list[ValidationIssue]:
    """S4: supersedes_fact_id equal to the payload's own fact_id."""
    if not isinstance(payload, dict):
        return []
    fact_id, supersedes = payload.get("fact_id"), payload.get("supersedes_fact_id")
    if isinstance(fact_id, str) and isinstance(supersedes, str) and fact_id == supersedes:
        return [ValidationIssue(
            SUPERSEDES_REQUIRED, "/supersedes_fact_id",
            f"supersedes_fact_id {supersedes!r} equals the payload fact_id (rule S4)")]
    return []


def _s5_envelope_time_order(payload, ctx: _Context) -> list[ValidationIssue]:
    """S5: observed_at earlier than source_available_at (physics: a source
    cannot be observed before it exists — the only ordering implemented)."""
    if not isinstance(payload, dict):
        return []
    observed, available = payload.get("observed_at"), payload.get("source_available_at")
    if not (isinstance(observed, str) and isinstance(available, str)):
        return []
    observed_dt, available_dt = _parse_iso_datetime(observed), _parse_iso_datetime(available)
    if observed_dt is None or available_dt is None:
        return []
    try:
        time_travel = observed_dt < available_dt
    except TypeError:  # mixed naive/aware stays unjudgeable here
        return []
    if time_travel:
        return [ValidationIssue(
            SCHEMA_VIOLATION, "/observed_at",
            f"observed_at {observed!r} precedes source_available_at {available!r} (rule S5)")]
    return []


def _s6_real_calendar_values(payload, ctx: _Context) -> list[ValidationIssue]:
    """S6: format date / date-time strings must be real calendar values.

    The calendar-typed property set is collected once per contract from the
    ``format`` keyword and the ISO-8601 ``pattern`` declarations; date-shaped
    strings inside quote/prose fields are not calendar-typed and are not
    checked.  No jsonschema FormatChecker or rfc3339 dependency.
    """
    issues = []
    for obj, keys in _iter_objects(payload):
        for key in sorted(obj):
            kind = ctx.calendar_props.get(key) if isinstance(key, str) else None
            value = obj.get(key)
            if kind is None or not isinstance(value, str):
                continue
            if not _calendar_ok(value, kind):
                issues.append(ValidationIssue(
                    SCHEMA_VIOLATION, _pointer(list(keys) + [key]),
                    f"{key} {value!r} is not a real calendar {kind} value (rule S6)"))
    return issues


def _s7_uri_schemes(payload, ctx: _Context) -> list[ValidationIssue]:
    """S7: data:/vbscript:/blob: scheme in a text_safe-governed string."""
    issues = []
    for obj, keys in _iter_objects(payload):
        for key in sorted(obj):
            value = obj.get(key)
            if key not in ctx.text_safe_props or not isinstance(value, str):
                continue
            if _SCHEME_RE.search(value):
                issues.append(ValidationIssue(
                    INJECTION_PATTERN, _pointer(list(keys) + [key]),
                    f"{key} carries a data:/vbscript:/blob: scheme (rule S7)"))
    return issues


def _role_marker_hit(text: str, patterns: tuple) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _s8_split_role_markers(payload, ctx: _Context) -> list[ValidationIssue]:
    """S8: a role marker split across two text_safe-governed string fields.

    For each ordered pair of distinct governed values (a, b) the joins
    a+b and a+" "+b are tested against the role-marker branches of text_safe
    ONLY, and only when neither a nor b alone matches those branches (a
    field that already matches is rejected by the schema pass; re-reporting
    it here would double-count the same defect).
    """
    governed = []
    for obj, keys in _iter_objects(payload):
        for key in sorted(obj):
            value = obj.get(key)
            if key in ctx.text_safe_props and isinstance(value, str):
                governed.append((_pointer(list(keys) + [key]), value))
    issues = []
    if not ctx.role_marker_patterns:
        return issues
    for i in range(len(governed)):
        for j in range(len(governed)):
            if i == j:
                continue
            path_a, a = governed[i]
            path_b, b = governed[j]
            if a == b:
                continue
            if _role_marker_hit(a, ctx.role_marker_patterns) or \
                    _role_marker_hit(b, ctx.role_marker_patterns):
                continue
            if _role_marker_hit(a + b, ctx.role_marker_patterns) or \
                    _role_marker_hit(a + " " + b, ctx.role_marker_patterns):
                issues.append(ValidationIssue(
                    INJECTION_PATTERN, path_b,
                    "role marker split across text_safe-governed fields (rule S8)"))
    return issues


def _s9_identifier_form_vocabulary(payload, ctx: _Context) -> list[ValidationIssue]:
    """S9 / R5(b): identifier-form vocabulary tokens inside any string value."""
    issues = []
    for obj, keys in _iter_objects(payload):
        for key in sorted(obj):
            value = obj.get(key)
            if not isinstance(value, str):
                continue
            match = _JOINED_VOCAB_RE.search(value)
            if match:
                issues.append(ValidationIssue(
                    FORBIDDEN_VOCABULARY, _pointer(list(keys) + [key]),
                    f"identifier-form forbidden vocabulary {match.group(0)!r} "
                    f"in string value (rule S9)"))
    return issues


def _s10_llm_provenance(payload, ctx: _Context) -> list[ValidationIssue]:
    """S10 / R5(c): llm / gpt / synthetic (or llm+generated) in an identifier
    or profile field — DNR:KILL-LLM-ORIGINATION at the provenance surface."""
    issues = []
    for obj, keys in _iter_objects(payload):
        for key in sorted(obj):
            value = obj.get(key)
            if not (isinstance(key, str) and key.endswith(_IDENTIFIER_SUFFIXES)):
                continue
            if not isinstance(value, str):
                continue
            tokens = frozenset(t for t in re.split(r"[-_.]+", value.lower()) if t)
            if tokens & _PROVENANCE_TOKENS or {"llm", "generated"} <= tokens:
                issues.append(ValidationIssue(
                    FORBIDDEN_VOCABULARY, _pointer(list(keys) + [key]),
                    f"{key} {value!r} carries LLM-originated provenance (rule S10)"))
    return issues


def _s11_range_bounds(payload, ctx: _Context) -> list[ValidationIssue]:
    """S11: an amount range whose low exceeds its high."""
    issues = []
    for obj, keys in _iter_objects(payload):
        low, high = obj.get("low"), obj.get("high")
        if _is_number(low) and _is_number(high) and low > high:
            issues.append(ValidationIssue(
                SCHEMA_VIOLATION, _pointer(list(keys) + ["high"]),
                f"range low {low} exceeds high {high} (rule S11)"))
    return issues


def _s12_self_counterparty(payload, ctx: _Context) -> list[ValidationIssue]:
    """S12: counterparty_company_id equal to the event issuer company id."""
    issues = []
    for obj, keys in _iter_objects(payload):
        company_id = obj.get("company_id")
        counterparty = obj.get("counterparty_company_id")
        if not isinstance(company_id, str):
            continue
        values = counterparty if isinstance(counterparty, list) else [counterparty]
        if any(isinstance(v, str) and v == company_id for v in values):
            issues.append(ValidationIssue(
                SCHEMA_VIOLATION, _pointer(list(keys) + ["counterparty_company_id"]),
                f"counterparty_company_id equals the issuer company_id {company_id!r} (rule S12)"))
    return issues


def _s13_period_bounds(payload, ctx: _Context) -> list[ValidationIssue]:
    """S13: a fiscal period whose end_year precedes its year."""
    issues = []
    for obj, keys in _iter_objects(payload):
        year, end_year = obj.get("year"), obj.get("end_year")
        if _is_number(year) and _is_number(end_year) and end_year < year:
            issues.append(ValidationIssue(
                SCHEMA_VIOLATION, _pointer(list(keys) + ["end_year"]),
                f"end_year {end_year} precedes year {year} (rule S13)"))
    return issues


_SEMANTIC_RULES: tuple[Callable[[object, "_Context"], list[ValidationIssue]], ...] = (
    _s1_non_finite_numbers,
    _s2_ordered_pairs,
    _s3_span_within_segment,
    _s4_no_self_supersession,
    _s5_envelope_time_order,
    _s6_real_calendar_values,
    _s7_uri_schemes,
    _s8_split_role_markers,
    _s9_identifier_form_vocabulary,
    _s10_llm_provenance,
    _s11_range_bounds,
    _s12_self_counterparty,
    _s13_period_bounds,
)


def _semantic_issues(payload, ctx: _Context) -> list[ValidationIssue]:
    """The S1-S13 semantic layer, merged after the schema pass.

    A rule that cannot evaluate (field absent, wrong type the schema already
    rejects) emits nothing and never raises: each rule runs under a guard
    that discards its output if the rule itself fails, so no semantic rule
    can turn a validation into a crash.
    """
    issues: list[ValidationIssue] = []
    for rule in _SEMANTIC_RULES:
        try:
            issues.extend(rule(payload, ctx))
        except Exception:  # frozen spec: a rule that cannot evaluate emits nothing
            continue
    return issues


# --------------------------------------------------------------- strict loading

class _StrictPairs(dict):
    """dict that keeps json last-wins semantics while recording duplicate keys."""

    duplicate_keys: list

    def __init__(self, pairs):
        super().__init__()
        self.duplicate_keys = []
        seen = set()
        for key, value in pairs:
            if key in seen and key not in self.duplicate_keys:
                self.duplicate_keys.append(key)
            seen.add(key)
            self[key] = value


def _reject_constant(token: str):
    raise StrictJsonError(
        SCHEMA_VIOLATION, "",
        f"non-finite JSON constant {token!r} (rule S1)")


def load_strict(text: str) -> object:
    """json.loads that rejects duplicate object keys and non-finite constants.

    A duplicate key raises :class:`StrictJsonError` with code
    ``injection_pattern`` and the JSON pointer of the (deterministically
    first) object holding it; a bare NaN/Infinity/-Infinity token raises
    with code ``schema_violation`` (the parser exposes no position, so the
    path is the empty pointer).  Well-formed input returns exactly what
    ``json.loads`` returns.
    """
    payload = json.loads(text, object_pairs_hook=_StrictPairs, parse_constant=_reject_constant)
    duplicates = []

    def walk(node, keys):
        if isinstance(node, _StrictPairs):
            for key in node.duplicate_keys:
                duplicates.append((_pointer(list(keys)), key))
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, list(keys) + [key])
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, list(keys) + [i])

    walk(payload, [])
    if duplicates:
        path, key = min(duplicates)
        raise StrictJsonError(
            INJECTION_PATTERN, path, f"duplicate JSON object key {key!r}")
    return payload


# ---------------------------------------------------------------------- public

def validate_event(payload: dict, *, contract: dict | None = None) -> ValidationReport:
    """Validate one news-impact payload against the frozen contract.

    Validates with the Draft the contract itself declares (2020-12).  The
    top-level oneOf over templates is dispatched on each branch's ``schema``
    const so issues point at the real node; a payload naming no branch gets
    one ``schema_violation`` at ``/schema``.  After the schema pass the
    semantic layer (S1-S13) merges its issues into the same sorted,
    de-duplicated report.  Every issue carries exactly one of
    :data:`REASON_CODES`.  The payload is never mutated.
    """
    ctx = _Context.build(contract if contract is not None else load_contract())
    issues = _schema_issues(payload, ctx)
    issues.extend(_forbidden_vocabulary_issues(payload))
    issues.extend(_supersedes_issues(payload))
    issues.extend(_semantic_issues(payload, ctx))
    return _finalize(_merge(issues), payload)


def validate_batch(payloads: Iterable[dict], *, contract: dict | None = None) -> list[ValidationReport]:
    """Validate many payloads, loading and preparing the contract once."""
    ctx = _Context.build(contract if contract is not None else load_contract())
    reports = []
    for payload in payloads:
        issues = _schema_issues(payload, ctx)
        issues.extend(_forbidden_vocabulary_issues(payload))
        issues.extend(_supersedes_issues(payload))
        issues.extend(_semantic_issues(payload, ctx))
        reports.append(_finalize(_merge(issues), payload))
    return reports


def validate_text(text: str, *, contract: dict | None = None) -> ValidationReport:
    """Strict-load raw text, then validate: the single raw-text entry point.

    A :class:`StrictJsonError` becomes a rejected report carrying exactly
    that one issue with ``fact_id`` None; well-formed text is validated by
    :func:`validate_event`.
    """
    try:
        payload = load_strict(text)
    except StrictJsonError as exc:
        return ValidationReport(
            ok=False, issues=(ValidationIssue(exc.code, exc.path, str(exc)),),
            fact_id=None)
    return validate_event(payload, contract=contract)


def summarize(reports: Iterable[ValidationReport]) -> dict:
    """Aggregate reports; every code in REASON_CODES is present, keys sorted."""
    materialized = list(reports)
    by_code = {code: 0 for code in sorted(REASON_CODES)}
    for report in materialized:
        for issue in report.issues:
            by_code[issue.code] = by_code.get(issue.code, 0) + 1
    return {
        "by_code": dict(sorted(by_code.items())),
        "ok": sum(1 for r in materialized if r.ok),
        "rejected": sum(1 for r in materialized if not r.ok),
        "total": len(materialized),
    }


def project_display(payload: dict, *, contract: dict | None = None) -> dict:
    """Deep copy with seat rulings R1/R2 applied, for DISPLAY only.

    The owner's proof object is text_sha256 + locator + receipt, never the
    excerpt (documents.py:316, :429).  So ``display_excerpt`` becomes None
    whenever the owner excerpt would fail the contract's own
    ``source_span_v1.display_excerpt`` subschema: a text_safe not-clause
    (R1: URL-bearing, instruction-shaped, control characters, ...) or the
    500-char cap (R2), or a data:/vbscript:/blob: scheme, which rule S7
    makes part of text safety.  The excerpt is never truncated: a cut quote
    shown without a marker would misstate the source, and the closed
    source_span_v1 admits no truncation flag.  The input is never mutated.
    """
    root = contract if contract is not None else load_contract()
    rule = dict(root["$defs"]["source_span_v1"]["properties"]["display_excerpt"])
    rule["$defs"] = root["$defs"]
    admits_schema = _jsv.validator_for(root)(rule).is_valid

    def admits(value: str) -> bool:
        return admits_schema(value) and not _SCHEME_RE.search(value)
    out = copy.deepcopy(payload)

    def walk(node):
        if isinstance(node, dict):
            for key in list(node):
                if key == "display_excerpt" and isinstance(node[key], str) and not admits(node[key]):
                    node[key] = None
                walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(out)
    return out


# -------------------------------------------------------------------------- CLI

def _file_reports(path: Path, contract: dict) -> list[ValidationReport]:
    """One file -> reports: strict-parsed as a whole, then each element validated."""
    text = path.read_text(encoding="utf-8")
    try:
        payload = load_strict(text)
    except StrictJsonError as exc:
        return [ValidationReport(
            ok=False, issues=(ValidationIssue(exc.code, exc.path, str(exc)),),
            fact_id=None)]
    items = payload if isinstance(payload, list) else [payload]
    return validate_batch(items, contract=contract)


def main(argv: list[str] | None = None) -> int:
    """CLI entry: ``python -m engine.news_impact.validate PATH [--json]``."""
    parser = argparse.ArgumentParser(
        prog="python -m engine.news_impact.validate",
        description="Validate news-impact payload JSON against the frozen contract.")
    parser.add_argument("path", help=".json file holding one payload or a list, or a directory of .json files")
    parser.add_argument("--json", action="store_true", help="print the summarize() dict instead of per-payload lines")
    args = parser.parse_args(argv)

    try:
        path = Path(args.path)
        files = sorted(path.glob("*.json")) if path.is_dir() else [path]
        contract = load_contract()
        reports = []
        for file in files:
            reports.extend(_file_reports(file, contract))
    except ContractMismatch as exc:
        print(f"contract mismatch: {exc}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summarize(reports), sort_keys=True))
    else:
        for index, report in enumerate(reports):
            name = report.fact_id if report.fact_id is not None else str(index)
            codes = ",".join(sorted({issue.code for issue in report.issues}))
            print(f"{name}\t{'OK' if report.ok else 'REJECT'}\t{codes}")
    return 0 if all(report.ok for report in reports) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
