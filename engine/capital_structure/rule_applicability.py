"""Rule-applicability pack for Capital Structure Intelligence V2 (task L0).

L0 freezes the reviewed current and historical rule text that the capacity
(C1) and route (G0) waves evaluate against: Form S-3 General Instructions
I.B.1/I.B.6, Form F-3 I.B.1/I.B.5, 17 CFR 239.13(b)(1), 239.33(b)(1) and
230.401(g)(3) with their dated eCFR editions, the adopting Release 33-8878, and
the E0-qualified SEC staff interpretations and Nasdaq Rule 5635 excerpts. Each
rule carries dated windows saying on which days its exact text is verified,
only bracketed between qualified editions, or not known at all.

The pack itself is a config artifact,
``config/capital_structure_rule_applicability_pack.v1.json``. This module reads
and validates it against the E0 reference pack it pins, answers the eight
official E0 rule examples from their inputs, and exposes the two arithmetic
bounds the examples rest on (the I.B.6 one-third pool and the Nasdaq 20%
Issuance threshold). It never fetches and never writes.

Acceptance rows pinned here (masterplan §15):

* A12 - rule, staff interpretation, issuer assertion and proposal stay
  distinct; proposed Release 33-11418 is excluded and never evaluated as law.
* A13 - official rule examples and transition conditions are tested without
  collapsing Form S-3 and Form F-3 or their distinct instruction numbers.
* A14 - SEC registration does not by itself decide Nasdaq public-offering
  treatment and does not waive any other approval.
* A20 - every bound compares compatible units, share/price basis and
  effective intervals; unknown never becomes zero or infinity.

Nothing here scores, ranks, sizes or predicts (A48).
"""
from __future__ import annotations

import calendar
import copy
import hashlib
import json
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_DOWN, Decimal
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from engine.capital_structure import reference_qualification as rq
from engine.capital_structure.issuer_state_contracts import (
    FORBIDDEN_PROPERTY_PATTERN,
    Constraint,
    ContractViolation,
    EvidenceRef,
    Quantity,
    RulePack,
    RuleRef,
    Unknown,
    sha256_of,
    stable_id,
)

RULE_APPLICABILITY_PACK_SCHEMA = "capital_structure.rule_applicability_pack.v1"
RULE_APPLICABILITY_PACK_VERSION = "capital-structure-rule-applicability/1.2.0"
RULE_APPLICABILITY_PACK_RELPATH = Path("config") / "capital_structure_rule_applicability_pack.v1.json"
REPO_ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_MANIFEST_ID = "capital_structure.rule_applicability.L0"
EXCLUDED_PROPOSALS = frozenset({"sec_release_33_11418_registered_offering_reform"})
BABY_SHELF_FLOAT_THRESHOLD_USD = Decimal("75000000")
FLOAT_MEASUREMENT_LOOKBACK_DAYS = 60
NASDAQ_TWENTY_PERCENT = Decimal("0.2")

SOURCE_CLASSES = frozenset({"binding_rule", "edition_index"})
# Only these may become a rule in the pack. Proposals and issuer assertions are
# never rules here (A12); edition indices only date the text they index.
PACK_RULE_CLASSES = frozenset({"binding_rule", "staff_interpretation"})
VERIFIED_WINDOW_KINDS = frozenset({"version_index", "point", "amendment_trail", "interpretation_dated"})
BRACKETED_WINDOW_KINDS = frozenset({"bracket"})
BEFORE_FIRST_WINDOW = frozenset({"withheld", "not_in_force"})
RULE_STATES = ("verified", "bracketed", "beyond_window", "withheld", "not_in_force")
ANSWER_STATUSES = ("answered", "conditional", "inapplicable", "not_addressed", "withheld")
_UNKNOWN = "unknown"


class RuleApplicabilityError(ValueError):
    """The rule-applicability pack or a query against it is inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuleApplicabilityError(message)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized_digest(text: str) -> str:
    """Typography-blind digest: casefolded alphanumerics only."""
    return _sha("".join(ch for ch in text.casefold() if ch.isalnum()))


def _iso(value: Any, name: str) -> str:
    _require(isinstance(value, str), f"{name}: ISO date required, got {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise RuleApplicabilityError(f"{name}: {value!r} is not an ISO date") from exc
    return value


def _walk_keys(value: Any, where: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(not FORBIDDEN_PROPERTY_PATTERN.match(str(key)), f"{where}: forbidden property {key!r} (A48)")
            _walk_keys(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _walk_keys(item, f"{where}[{index}]")


def _record(value: Any) -> Any:
    if hasattr(value, "as_record"):
        return value.as_record()
    if is_dataclass(value):
        return {item.name: _record(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {key: _record(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_record(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Pack records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleSpan:
    span_id: str
    source_id: str
    chars: int
    sha256: str
    normalized_sha256: str
    text: str | None
    same_as: str | None


@dataclass(frozen=True)
class RuleWindow:
    """Days on which a rule's text is pinned to one exact digest."""

    kind: str
    start: str
    end: str
    sha256: str
    span_id: str | None = None
    reference_span_label: str | None = None

    @property
    def verified(self) -> bool:
        return self.kind in VERIFIED_WINDOW_KINDS

    def covers(self, as_of: str) -> bool:
        return self.start <= as_of <= self.end


@dataclass(frozen=True)
class ApplicableRule:
    rule_id: str
    binding_class: str
    enforceable: bool
    citation: str
    form: str | None
    instruction: str | None
    span_ids: tuple[str, ...]
    reference_span_labels: tuple[str, ...]
    windows: tuple[RuleWindow, ...]
    before_first_window: str
    not_in_force_before: str | None
    required_issuer_facts: tuple[str, ...]
    interpretation_date: str | None
    note: str | None

    def rule_ref(self) -> RuleRef:
        effective_from = self.not_in_force_before or self.interpretation_date
        return RuleRef(
            rule_id=self.rule_id,
            binding_class=self.binding_class,
            citation=self.citation,
            enforceable=self.enforceable,
            effective_from=effective_from,
            required_issuer_facts=self.required_issuer_facts,
        )


@dataclass(frozen=True)
class PackExample:
    example_id: str
    rule_ids: tuple[str, ...]
    negative: bool
    reference_digest: str


@dataclass(frozen=True)
class RuleApplicabilityPack:
    schema: str
    version: str
    task: str
    qualified_on: str
    masterplan: Mapping[str, Any]
    acceptance_rows: tuple[str, ...]
    rule_pack_id: str
    jurisdiction: str
    venues: tuple[str, ...]
    forms: tuple[str, ...]
    sources: Mapping[str, Mapping[str, Any]]
    spans: Mapping[str, RuleSpan]
    rules: Mapping[str, ApplicableRule]
    examples: Mapping[str, PackExample]
    excluded: tuple[Mapping[str, Any], ...]
    gaps: Mapping[str, Mapping[str, Any]]
    findings: tuple[str, ...]
    reference: rq.ReferencePack
    file_sha256: str

    def rule(self, rule_id: str) -> ApplicableRule:
        _require(rule_id in self.rules, f"unknown rule {rule_id!r}")
        return self.rules[rule_id]

    def span(self, span_id: str) -> RuleSpan:
        _require(span_id in self.spans, f"unknown span {span_id!r}")
        return self.spans[span_id]

    def span_text(self, span_id: str) -> str:
        span = self.span(span_id)
        return self.span(span.same_as).text if span.same_as else span.text  # type: ignore[return-value]

    def example(self, example_id: str) -> PackExample:
        _require(example_id in self.examples, f"unknown example {example_id!r}")
        return self.examples[example_id]

    def reference_example(self, example_id: str) -> rq.RuleExample:
        for example in rq.rule_examples(self.reference):
            if example.example_id == example_id:
                return example
        raise RuleApplicabilityError(f"example {example_id!r} is not an E0 rule example")


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def _parse_span(raw: Mapping[str, Any]) -> RuleSpan:
    text = raw.get("text")
    same_as = raw.get("same_as")
    _require((text is None) != (same_as is None), f"span {raw.get('span_id')!r}: exactly one of text/same_as")
    span = RuleSpan(
        span_id=raw["span_id"],
        source_id=raw["source_id"],
        chars=raw["chars"],
        sha256=raw["sha256"],
        normalized_sha256=raw["normalized_sha256"],
        text=text,
        same_as=same_as,
    )
    if text is not None:
        _require(len(text) == span.chars, f"span {span.span_id}: chars {span.chars} != {len(text)}")
        _require(_sha(text) == span.sha256, f"span {span.span_id}: text does not match its sha256")
        _require(normalized_digest(text) == span.normalized_sha256, f"span {span.span_id}: normalized digest mismatch")
    return span


def _parse_window(raw: Mapping[str, Any], rule_id: str) -> RuleWindow:
    kind = raw.get("kind")
    _require(kind in VERIFIED_WINDOW_KINDS | BRACKETED_WINDOW_KINDS, f"rule {rule_id}: unknown window kind {kind!r}")
    window = RuleWindow(
        kind=kind,
        start=_iso(raw.get("start"), f"rule {rule_id} window.start"),
        end=_iso(raw.get("end"), f"rule {rule_id} window.end"),
        sha256=raw["sha256"],
        span_id=raw.get("span_id"),
        reference_span_label=raw.get("reference_span_label"),
    )
    _require(window.start <= window.end, f"rule {rule_id}: window ends before it starts")
    _require(
        (window.span_id is None) != (window.reference_span_label is None),
        f"rule {rule_id}: a window names exactly one span_id or reference_span_label",
    )
    return window


def _parse_rule(raw: Mapping[str, Any]) -> ApplicableRule:
    rule_id = raw["rule_id"]
    windows = tuple(_parse_window(item, rule_id) for item in raw.get("windows", ()))
    _require(len(windows) > 0, f"rule {rule_id}: at least one window")
    _require(
        [w.start for w in windows] == sorted(w.start for w in windows),
        f"rule {rule_id}: windows must be ordered by start",
    )
    rule = ApplicableRule(
        rule_id=rule_id,
        binding_class=raw["binding_class"],
        enforceable=raw["enforceable"],
        citation=raw["citation"],
        form=raw.get("form"),
        instruction=raw.get("instruction"),
        span_ids=tuple(raw.get("span_ids", ())),
        reference_span_labels=tuple(raw.get("reference_span_labels", ())),
        windows=windows,
        before_first_window=raw["before_first_window"],
        not_in_force_before=raw.get("not_in_force_before"),
        required_issuer_facts=tuple(raw.get("required_issuer_facts", ())),
        interpretation_date=raw.get("interpretation_date"),
        note=raw.get("note"),
    )
    _require(
        rule.binding_class in PACK_RULE_CLASSES,
        f"rule {rule_id}: class {rule.binding_class!r} may not enter the pack (A12)",
    )
    try:
        rule.rule_ref()
    except ContractViolation as exc:
        raise RuleApplicabilityError(f"rule {rule_id}: {exc}") from exc
    _require(rule.before_first_window in BEFORE_FIRST_WINDOW, f"rule {rule_id}: before_first_window")
    if rule.before_first_window == "not_in_force":
        _require(
            rule.not_in_force_before == windows[0].start,
            f"rule {rule_id}: not_in_force_before must equal the first window start",
        )
    else:
        _require(rule.not_in_force_before is None, f"rule {rule_id}: not_in_force_before without not_in_force")
    if rule.binding_class == "staff_interpretation":
        _require(
            rule.interpretation_date == windows[0].start,
            f"rule {rule_id}: a staff interpretation is dated by its first window",
        )
    else:
        _require(rule.interpretation_date is None, f"rule {rule_id}: only interpretations carry an interpretation date")
    return rule


def parse_rule_applicability_pack(
    raw: Mapping[str, Any],
    *,
    reference_pack: rq.ReferencePack | None = None,
    reference_file_sha256: str | None = None,
    file_sha256: str = "",
) -> RuleApplicabilityPack:
    _walk_keys(raw, "rule_applicability_pack")
    _require(raw.get("schema") == RULE_APPLICABILITY_PACK_SCHEMA, f"schema {raw.get('schema')!r}")
    _require(raw.get("version") == RULE_APPLICABILITY_PACK_VERSION, f"version {raw.get('version')!r}")
    _require(raw.get("task") == "L0", f"task {raw.get('task')!r}")
    qualified_on = _iso(raw.get("qualified_on"), "qualified_on")
    window_kinds = raw.get("window_kinds", {})
    _require(
        set(window_kinds.get("verified", ())) == VERIFIED_WINDOW_KINDS
        and set(window_kinds.get("bracketed", ())) == BRACKETED_WINDOW_KINDS,
        "window_kinds drifted from the reader",
    )

    reference_meta = raw["reference_pack"]
    _require(reference_meta.get("schema") == rq.REFERENCE_PACK_SCHEMA, "reference_pack.schema")
    if reference_pack is None:
        reference_path = REPO_ROOT / reference_meta["path"]
        reference_pack = rq.load_reference_pack(reference_path)
        reference_file_sha256 = rq.file_digest(reference_path)
    if reference_file_sha256 is not None:
        _require(
            reference_file_sha256 == reference_meta["sha256_at_qualification"],
            "the E0 reference pack changed since L0 was qualified; requalify L0",
        )
    e0_spans = {span.label: span for source in reference_pack.sources for span in source.spans}
    pinned_spans: Mapping[str, str] = reference_meta["pinned_spans"]
    for label, digest in pinned_spans.items():
        _require(label in e0_spans, f"pinned span {label!r} is not an E0 span")
        _require(e0_spans[label].sha256 == digest, f"pinned span {label!r} no longer matches E0")

    sources: dict[str, Mapping[str, Any]] = {}
    for source in raw["sources"]:
        source_id = source["source_id"]
        _require(source_id not in sources, f"duplicate source {source_id!r}")
        _require(source_id not in EXCLUDED_PROPOSALS, f"excluded proposal {source_id!r} appears as a source (A12)")
        _require(source.get("source_class") in SOURCE_CLASSES, f"source {source_id}: class {source.get('source_class')!r}")
        _require(
            source.get("enforceable") is (source["source_class"] == "binding_rule"),
            f"source {source_id}: enforceable iff binding_rule",
        )
        sources[source_id] = source

    spans: dict[str, RuleSpan] = {}
    for item in raw["spans"]:
        span = _parse_span(item)
        _require(span.span_id not in spans, f"duplicate span {span.span_id!r}")
        _require(span.source_id in sources, f"span {span.span_id}: unknown source {span.source_id!r}")
        spans[span.span_id] = span
    for span in spans.values():
        if span.same_as is None:
            continue
        _require(span.same_as in spans, f"span {span.span_id}: same_as target {span.same_as!r} missing")
        target = spans[span.same_as]
        _require(target.same_as is None, f"span {span.span_id}: same_as must point at stored text")
        _require(
            (span.chars, span.sha256, span.normalized_sha256) == (target.chars, target.sha256, target.normalized_sha256),
            f"span {span.span_id}: same_as digests differ from {target.span_id}",
        )

    rules: dict[str, ApplicableRule] = {}
    for item in raw["rules"]:
        rule = _parse_rule(item)
        _require(rule.rule_id not in rules, f"duplicate rule {rule.rule_id!r}")
        for span_id in rule.span_ids:
            _require(span_id in spans, f"rule {rule.rule_id}: unknown span {span_id!r}")
        for label in rule.reference_span_labels:
            _require(label in pinned_spans, f"rule {rule.rule_id}: reference label {label!r} is not pinned")
        for window in rule.windows:
            if window.span_id is not None:
                _require(window.span_id in rule.span_ids, f"rule {rule.rule_id}: window span not cited by the rule")
                expected = spans[window.span_id].sha256
            else:
                _require(
                    window.reference_span_label in rule.reference_span_labels,
                    f"rule {rule.rule_id}: window label not cited by the rule",
                )
                expected = pinned_spans[window.reference_span_label]
            _require(window.sha256 == expected, f"rule {rule.rule_id}: window {window.start}..{window.end} digest mismatch")
        rules[rule.rule_id] = rule

    reference_examples = {example.example_id: example for example in rq.rule_examples(reference_pack)}
    pinned_examples: Mapping[str, str] = reference_meta["pinned_examples"]
    examples: dict[str, PackExample] = {}
    for item in raw["examples"]:
        example = PackExample(
            example_id=item["example_id"],
            rule_ids=tuple(item["rule_ids"]),
            negative=item["negative"],
            reference_digest=item["reference_digest"],
        )
        _require(example.example_id not in examples, f"duplicate example {example.example_id!r}")
        _require(example.example_id in reference_examples, f"example {example.example_id!r} is not an E0 example")
        ref = reference_examples[example.example_id]
        digest = sha256_of({"inputs": ref.inputs, "expected": ref.expected})
        _require(
            example.reference_digest == pinned_examples.get(example.example_id) == digest,
            f"example {example.example_id}: E0 inputs/expected changed since L0 was qualified",
        )
        _require(example.negative is ref.negative, f"example {example.example_id}: negative flag differs from E0")
        for rule_id in example.rule_ids:
            _require(rule_id in rules, f"example {example.example_id}: unknown rule {rule_id!r}")
        examples[example.example_id] = example
    _require(set(examples) == set(reference_examples), "L0 must answer exactly the E0 rule examples")

    excluded = tuple(raw.get("excluded", ()))
    excluded_ids = {item["source_id"] for item in excluded}
    _require(EXCLUDED_PROPOSALS <= excluded_ids, "Release 33-11418 must be listed as excluded (A12)")
    for item in excluded:
        _require(item.get("binding_class") == "proposed_reform", f"excluded {item['source_id']}: not a proposal")
        _require(item.get("enforceable") is False, f"excluded {item['source_id']}: a proposal is never enforceable")
        _require(
            reference_pack.source(item["source_id"]).source_class == "proposed_reform",
            f"excluded {item['source_id']}: E0 does not class it as a proposal",
        )
    for rule in rules.values():
        _require(
            not (set(rule.span_ids) | set(rule.reference_span_labels)) & excluded_ids,
            f"rule {rule.rule_id}: cites an excluded proposal",
        )

    gaps: dict[str, Mapping[str, Any]] = {}
    for gap in raw.get("gaps", ()):
        _require(gap["gap_id"] not in gaps, f"duplicate gap {gap['gap_id']!r}")
        gaps[gap["gap_id"]] = gap

    rule_pack = raw["rule_pack"]
    return RuleApplicabilityPack(
        schema=raw["schema"],
        version=raw["version"],
        task=raw["task"],
        qualified_on=qualified_on,
        masterplan=raw["masterplan"],
        acceptance_rows=tuple(raw["acceptance_rows"]),
        rule_pack_id=rule_pack["rule_pack_id"],
        jurisdiction=rule_pack["jurisdiction"],
        venues=tuple(rule_pack.get("venues", ())),
        forms=tuple(rule_pack.get("forms", ())),
        sources=sources,
        spans=spans,
        rules=rules,
        examples=examples,
        excluded=excluded,
        gaps=gaps,
        findings=tuple(raw.get("findings", ())),
        reference=reference_pack,
        file_sha256=file_sha256,
    )


def load_rule_applicability_pack(
    path: Path | None = None,
    *,
    reference_pack: rq.ReferencePack | None = None,
) -> RuleApplicabilityPack:
    target = path or REPO_ROOT / RULE_APPLICABILITY_PACK_RELPATH
    data = target.read_bytes()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuleApplicabilityError(f"{target}: not valid JSON") from exc
    return parse_rule_applicability_pack(raw, reference_pack=reference_pack, file_sha256=hashlib.sha256(data).hexdigest())


def select_rule_pack(
    jurisdiction: str, venue: str, form: str
) -> "RuleApplicabilityPack | Unknown":
    """The single qualified rule pack for a jurisdiction + venue + form (SPEC_G0 §2.3).

    One pack is qualified today; this function is the single point a second
    qualified pack plugs into.  A request outside the pack's ``rule_pack``
    ``jurisdiction``/``venues``/``forms`` returns the typed
    ``rule_pack_unqualified:{jurisdiction}:{venue}:{form}`` Unknown instead of a
    silent answer — never a defaulted pack.
    """
    pack = load_rule_applicability_pack()
    if (
        pack.jurisdiction == jurisdiction
        and venue in pack.venues
        and form in pack.forms
    ):
        return pack
    return Unknown(
        unknown_id=f"rule_pack_unqualified:{jurisdiction}:{venue}:{form}",
        description=(
            f"no qualified rule-applicability pack covers jurisdiction {jurisdiction!r}, "
            f"venue {venue!r} and form {form!r}; the qualified pack covers jurisdiction "
            f"{pack.jurisdiction!r}, venues {list(pack.venues)} and forms {list(pack.forms)}"
        ),
        resolving_fact=(
            f"a qualified rule-applicability pack carrying jurisdiction {jurisdiction!r}, "
            f"venue {venue!r} and form {form!r}"
        ),
        affects=(pack.rule_pack_id,),
    )


# ---------------------------------------------------------------------------
# Rule status as of a date
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleStatus:
    rule_id: str
    as_of: str
    state: str
    window: RuleWindow | None = None
    condition: str | None = None

    def as_record(self) -> dict[str, Any]:
        return _record({item.name: getattr(self, item.name) for item in fields(self)})


def rule_status_as_of(pack: RuleApplicabilityPack, rule_id: str, as_of: str) -> RuleStatus:
    """Whether the exact text of ``rule_id`` is known to govern on ``as_of``.

    ``verified``: a qualified edition, version index, amendment trail or dated
    interpretation pins the text on that day. ``bracketed``: the day lies
    between two qualified editions and the text is inferred, not retrieved.
    ``beyond_window``: the text was last verified before ``as_of`` and must be
    requalified. ``withheld``: no qualified text covers the day. ``not_in_force``:
    the rule had not been adopted.
    """
    _iso(as_of, "as_of")
    rule = pack.rule(rule_id)
    if rule.not_in_force_before is not None and as_of < rule.not_in_force_before:
        return RuleStatus(
            rule_id, as_of, "not_in_force",
            condition=f"{rule.citation} was not in force before {rule.not_in_force_before}",
        )
    covering = [window for window in rule.windows if window.covers(as_of)]
    verified = [window for window in covering if window.verified]
    if verified:
        return RuleStatus(rule_id, as_of, "verified", window=verified[-1])
    if covering:
        window = covering[-1]
        return RuleStatus(
            rule_id, as_of, "bracketed", window=window,
            condition=(
                f"{rule.citation} on {as_of} is bracketed between qualified editions "
                f"{window.start} and {window.end}, not verified edition by edition"
            ),
        )
    last = max(rule.windows, key=lambda window: window.end)
    if as_of > last.end:
        return RuleStatus(
            rule_id, as_of, "beyond_window", window=last,
            condition=f"{rule.citation} was last verified on {last.end}; requalify before relying on it on {as_of}",
        )
    reason = "before its first qualified window" if as_of < rule.windows[0].start else "between qualified windows"
    return RuleStatus(rule_id, as_of, "withheld", condition=f"no qualified text of {rule.citation} on {as_of} ({reason})")


def _withheld_unknown(pack: RuleApplicabilityPack, status: RuleStatus) -> Unknown:
    rule = pack.rule(status.rule_id)
    return Unknown(
        unknown_id=f"rule_text:{rule.rule_id}:{status.as_of}",
        description=status.condition or f"no qualified text of {rule.citation} on {status.as_of}",
        resolving_fact=f"the qualified text of {rule.citation} in force on {status.as_of}",
        affects=(rule.rule_id,),
    )


def build_rule_pack(
    pack: RuleApplicabilityPack, as_of: str
) -> tuple[RulePack | None, tuple[Unknown, ...], tuple[str, ...], tuple[str, ...]]:
    """Contract :class:`RulePack` of the rules whose text governs on ``as_of``.

    Returns the pack (``None`` when no rule qualifies), the unknowns for rules
    whose text is withheld, the bracketed/stale conditions, and the excluded
    proposal ids. Rules not yet in force are simply absent.
    """
    statuses = [rule_status_as_of(pack, rule_id, as_of) for rule_id in pack.rules]
    included = [s for s in statuses if s.state in ("verified", "bracketed", "beyond_window")]
    unknowns = tuple(_withheld_unknown(pack, s) for s in statuses if s.state == "withheld")
    conditions = tuple(s.condition for s in included if s.condition)
    excluded = tuple(sorted(item["source_id"] for item in pack.excluded))
    if not included:
        return None, unknowns, conditions, excluded
    rule_pack = RulePack(
        rule_pack_id=pack.rule_pack_id,
        version=pack.version,
        source_edition=f"{pack.task}:{pack.qualified_on}:{pack.file_sha256[:16] or 'unhashed'}",
        jurisdiction=pack.jurisdiction,
        effective_date=as_of,
        interpretation_date=pack.qualified_on,
        rules=tuple(pack.rule(s.rule_id).rule_ref() for s in included),
        venues=pack.venues,
        forms=pack.forms,
    )
    return rule_pack, unknowns, conditions, excluded


# ---------------------------------------------------------------------------
# Official example answers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuleAnswer:
    """One example answered from its inputs, with the authority it rests on."""

    example_id: str
    as_of: str
    status: str
    answer: Mapping[str, Any] | None
    unknowns: tuple[Unknown, ...] = ()
    conditions: tuple[str, ...] = ()
    rule_statuses: tuple[RuleStatus, ...] = ()
    authority: tuple[RuleRef, ...] = ()
    scope_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require(self.status in ANSWER_STATUSES, f"answer status {self.status!r}")
        if self.status in ("answered", "conditional"):
            _require(self.answer is not None, f"{self.example_id}: an answered example carries its answer")
        if self.status == "conditional":
            _require(len(self.conditions) > 0, f"{self.example_id}: a conditional answer names its conditions")
        if self.status == "withheld":
            _require(len(self.unknowns) > 0, f"{self.example_id}: a withheld answer names what would resolve it")
        _walk_keys(self.answer or {}, f"answer[{self.example_id}]")

    def as_record(self) -> dict[str, Any]:
        record = _record({item.name: getattr(self, item.name) for item in fields(self)})
        _walk_keys(record, f"answer[{self.example_id}]")
        return record


@dataclass(frozen=True)
class _Outcome:
    status: str
    answer: Mapping[str, Any] | None = None
    scope_notes: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    unknowns: tuple[Unknown, ...] = ()


def _input_unknown(example_id: str, key: str, why: str) -> Unknown:
    return Unknown(
        unknown_id=f"input:{example_id}:{key}",
        description=f"{key} is {why}",
        resolving_fact=f"the issuer fact {key} for this example",
        affects=(example_id,),
    )


def _known(inputs: Mapping[str, Any], key: str) -> bool:
    return key in inputs and inputs[key] is not None and inputs[key] != _UNKNOWN


def _bool(inputs: Mapping[str, Any], key: str) -> bool:
    value = inputs[key]
    _require(isinstance(value, bool), f"input {key}: true/false required, got {value!r}")
    return value


def _amount(inputs: Mapping[str, Any], key: str) -> Decimal:
    value = inputs[key]
    _require(
        isinstance(value, (int, str)) and not isinstance(value, bool),
        f"input {key}: integer or decimal string required, got {value!r}",
    )
    try:
        amount = Decimal(str(value))
    except ArithmeticError as exc:
        raise RuleApplicabilityError(f"input {key}: {value!r} is not a number") from exc
    _require(amount.is_finite() and amount >= 0, f"input {key}: a nonnegative amount is required")
    return amount


def _dollars(amount: Decimal) -> int | str:
    # Whole dollars stay integers (as the official examples state them);
    # anything finer is a decimal string, never a float.
    return int(amount) if amount == amount.to_integral_value() else format(amount, "f")


def _instruction_mismatch(example_id: str, key: str, value: Any, expected: str) -> _Outcome:
    return _Outcome(
        "not_addressed",
        scope_notes=(
            f"{example_id} interprets {expected}; {key}={value!r} is a distinct form or instruction "
            "this example does not address (A13)",
        ),
    )


def _example_116_21(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    if inputs["instrument"] != "private_equity_line":
        return _Outcome("not_addressed", scope_notes=(f"{example_id} addresses private equity lines only",))
    mode = inputs["registration_mode"]
    _require(mode in ("primary_offering", "resale_offering"), f"registration_mode {mode!r}")
    if mode != "primary_offering":
        return _Outcome(
            "inapplicable",
            scope_notes=(
                "C&DI 116.21 treats the equity line as a primary at-the-market offering; a resale "
                "registration of the same line is outside it",
            ),
        )
    return _Outcome(
        "answered",
        answer={
            "is_at_the_market_offering": True,
            "eligible_instructions": ["S-3 I.B.1", "S-3 I.B.6", "F-3 I.B.1", "F-3 I.B.5"],
            "instruction_numbering_differs_between_s3_and_f3": True,
            "baby_shelf_equity_line_cap": "one_third_of_public_float_at_agreement_execution",
        },
        scope_notes=(
            "Rule 415(a)(4) text is cited by the staff position but not qualified in L0 (gap rule_415_and_section_10_a_3_text)",
        ),
    )


def _example_116_22(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    if inputs["instruction"] != "S-3 I.B.6":
        return _instruction_mismatch(example_id, "instruction", inputs["instruction"], "Form S-3 I.B.6")
    exceeds = _bool(inputs, "supplement_amount_exceeds_remaining_one_third_capacity")
    return _Outcome(
        "answered",
        answer={
            "supplement_permitted": not exceeds,
            "measured_quantity": "amount_offered_in_supplement",
            "measurement_point": "immediately_prior_to_takedown",
            "counts_against_later_takedowns": "securities_actually_sold",
        },
        scope_notes=("expected sales within the limit do not change the measure: the amount offered is compared",),
    )


def _example_116_23(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    limit = _amount(inputs, "one_third_limit_usd")
    sold = _amount(inputs, "sold_to_date_usd")
    original = _amount(inputs, "june_7_supplement_usd")
    still_offered = _amount(inputs, "still_offered_under_june_7_supplement_usd")
    _require(still_offered <= original, "still_offered_under_june_7_supplement_usd exceeds the June 7 supplement")
    notes: list[str] = []
    offerable = limit - sold
    if offerable < 0:
        notes.append(f"sales of {_dollars(sold)} already exceed the one-third limit of {_dollars(limit)}")
        offerable = Decimal(0)
    room = offerable - still_offered
    if room < 0:
        notes.append("securities still offered under the June 7 supplement already exceed what may be offered")
        room = Decimal(0)
    return _Outcome(
        "answered",
        answer={
            "offerable_total_as_of_june_14_usd": _dollars(offerable),
            "max_june_14_supplement_usd": _dollars(room),
            "concurrent_continuous_offerings_count_against_limit": True,
        },
        scope_notes=tuple(notes),
    )


def _example_116_24(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    components = inputs["offering_components"]
    _require(isinstance(components, list) and all(isinstance(c, str) for c in components), "offering_components")
    if "warrants" not in components:
        return _Outcome("inapplicable", scope_notes=("no warrants are offered; Instruction 2's warrant measure does not arise",))
    return _Outcome(
        "answered",
        answer={"instruction_2_applies_to_warrant_market_value": True},
        scope_notes=("the warrants' exercisability window does not change the answer",),
    )


def _example_116_25(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    if inputs["takedown_instruction"] != "S-3 I.B.6":
        return _instruction_mismatch(example_id, "takedown_instruction", inputs["takedown_instruction"], "Form S-3 I.B.6")
    if inputs["concurrent_private_placement_resale_instruction"] != "S-3 I.B.3":
        return _instruction_mismatch(
            example_id,
            "concurrent_private_placement_resale_instruction",
            inputs["concurrent_private_placement_resale_instruction"],
            "Form S-3 I.B.3",
        )
    if not _bool(inputs, "public_float_below_75m_usd"):
        return _Outcome(
            "inapplicable",
            scope_notes=("public float of $75 million or more: the one-third limit does not apply (I.B.6 Instruction 3)",),
        )
    if not _bool(inputs, "same_investors"):
        return _Outcome("not_addressed", scope_notes=(f"{example_id} addresses a resale by the same investors only",))
    return _Outcome(
        "answered",
        answer={
            "resale_counts_against_ib6_capacity": True,
            "ib3_resale_permitted_without_sufficient_ib6_capacity_at_filing": False,
            "alternatives_if_insufficient": ["register_resale_on_form_s1", "wait_for_capacity"],
        },
    )


def _example_116_26(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    if inputs["supplement_filed_under"] != "S-3 I.B.1":
        return _instruction_mismatch(example_id, "supplement_filed_under", inputs["supplement_filed_under"], "Form S-3 I.B.1")
    if inputs["remains_s3_eligible_under"] != "S-3 I.B.6":
        return _instruction_mismatch(
            example_id, "remains_s3_eligible_under", inputs["remains_s3_eligible_under"], "Form S-3 I.B.6"
        )
    if not _bool(inputs, "atm_sales_agreement_with_named_agent"):
        return _Outcome("not_addressed", scope_notes=(f"{example_id} addresses an ATM programme with a named agent only",))
    if not _bool(inputs, "public_float_below_75m_at_next_10a3_update"):
        return _Outcome(
            "inapplicable",
            scope_notes=("public float stays at $75 million or more: no transition to I.B.6 occurs",),
        )
    condition = "prospectus_supplement_filed_before_the_10a3_update"
    return _Outcome(
        "conditional",
        answer={
            "staff_objects_to_continuing_full_supplement_amount": False,
            "condition": condition,
            "authority_kind": "staff_position_not_rule",
        },
        conditions=(condition,),
        scope_notes=(
            "a staff no-objection position, not a Commission rule; Section 10(a)(3) text is not qualified in L0 "
            "(gap rule_415_and_section_10_a_3_text)",
        ),
    )


def _example_5635_d_2(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    not_evaluated = "Nasdaq Rules 5635(a)-(c) and any other approval are not evaluated here (A14)"
    if inputs["listing_venue"] != "nasdaq":
        return _Outcome("inapplicable", scope_notes=("Rule 5635 binds Nasdaq-listed issuers only",))
    if _bool(inputs, "public_offering_per_im_5635_3"):
        return _Outcome(
            "inapplicable",
            scope_notes=("a public offering under IM-5635-3 is outside the 20% Issuance definition", not_evaluated),
        )
    price = inputs["price_relative_to_minimum_price"]
    _require(price in ("below", "at_or_above"), f"price_relative_to_minimum_price {price!r}")
    percent_common = _amount(inputs, "issuance_percent_of_common_outstanding_before")
    facts = list(pack.rule("nasdaq.5635.d.2").required_issuer_facts)
    is_twenty_percent: bool
    if percent_common >= 20:
        is_twenty_percent = True
    elif _known(inputs, "issuance_percent_of_voting_power_outstanding_before"):
        is_twenty_percent = _amount(inputs, "issuance_percent_of_voting_power_outstanding_before") >= 20
    else:
        return _Outcome(
            "withheld",
            unknowns=(
                _input_unknown(
                    example_id,
                    "issuance_percent_of_voting_power_outstanding_before",
                    "needed: below 20% of common stock, the voting-power prong of 5635(d)(1)(B) still applies",
                ),
            ),
        )
    required = is_twenty_percent and price == "below"
    notes = [not_evaluated]
    if not required:
        notes.insert(0, "Rule 5635(d)(2) is not triggered by these facts")
    return _Outcome(
        "answered",
        answer={"shareholder_approval_required_before_issuance": required, "required_issuer_facts": facts},
        scope_notes=tuple(notes),
    )


def _example_im_5635_3(example_id: str, inputs: Mapping[str, Any], pack: RuleApplicabilityPack) -> _Outcome:
    if not _bool(inputs, "registered_with_sec_before_closing"):
        return _Outcome("not_addressed", scope_notes=(f"{example_id} addresses an offering registered before closing",))
    return _Outcome(
        "answered",
        answer={"registration_alone_sufficient": False, "public_offering_status": "undetermined"},
        scope_notes=(
            "Nasdaq weighs the IM-5635-3 factors; this pack never decides public-offering status from registration (A14)",
        ),
    )


@dataclass(frozen=True)
class _Evaluator:
    run: Callable[[str, Mapping[str, Any], RuleApplicabilityPack], _Outcome]
    # Inputs the answer does not depend on: an unknown value never withholds it.
    irrelevant: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()


_EVALUATORS: dict[str, _Evaluator] = {
    "cdi_116_21_equity_line_is_at_the_market": _Evaluator(_example_116_21),
    "cdi_116_22_capacity_measured_against_amount_offered": _Evaluator(
        _example_116_22, irrelevant=frozenset({"actual_sales_expected_within_capacity"})
    ),
    "cdi_116_23_concurrent_continuous_offerings": _Evaluator(_example_116_23),
    "cdi_116_24_warrants_not_exercisable_within_12_months": _Evaluator(
        _example_116_24, irrelevant=frozenset({"warrants_exercisable_within_12_months"})
    ),
    "cdi_116_25_ib3_resale_counts_against_ib6_capacity": _Evaluator(_example_116_25),
    "cdi_116_26_atm_supplement_continues_after_transition_to_baby_shelf": _Evaluator(_example_116_26),
    "nasdaq_5635_d_2_twenty_percent_below_minimum_price": _Evaluator(
        _example_5635_d_2, optional=frozenset({"issuance_percent_of_voting_power_outstanding_before"})
    ),
    "nasdaq_im_5635_3_registration_alone_is_not_a_public_offering": _Evaluator(
        _example_im_5635_3, irrelevant=frozenset({"other_public_offering_factors"})
    ),
}


def evaluate_example(
    pack: RuleApplicabilityPack,
    example_id: str,
    inputs: Mapping[str, Any] | None = None,
    *,
    as_of: str | None = None,
) -> RuleAnswer:
    """Answer one official E0 rule example from ``inputs`` on ``as_of``.

    ``inputs`` replaces the E0 example inputs wholesale (defaults to them);
    a missing or ``"unknown"`` input withholds the answer unless the answer
    does not depend on it. ``as_of`` defaults to the pack's qualification day.
    """
    example = pack.example(example_id)
    reference = pack.reference_example(example_id)
    evaluator = _EVALUATORS.get(example_id)
    _require(evaluator is not None, f"no evaluator for example {example_id!r}")
    day = _iso(as_of or pack.qualified_on, "as_of")
    supplied = copy.deepcopy(dict(reference.inputs if inputs is None else inputs))
    allowed = set(reference.inputs) | evaluator.optional
    unexpected = sorted(set(supplied) - allowed)
    _require(not unexpected, f"{example_id}: unexpected inputs {unexpected}")

    statuses = tuple(rule_status_as_of(pack, rule_id, day) for rule_id in example.rule_ids)
    authority = tuple(pack.rule(rule_id).rule_ref() for rule_id in example.rule_ids)
    base = dict(example_id=example_id, as_of=day, rule_statuses=statuses, authority=authority)

    not_in_force = [s for s in statuses if s.state == "not_in_force"]
    if not_in_force:
        return RuleAnswer(status="inapplicable", answer=None, scope_notes=tuple(s.condition for s in not_in_force), **base)
    withheld = [s for s in statuses if s.state == "withheld"]
    if withheld:
        return RuleAnswer(
            status="withheld", answer=None, unknowns=tuple(_withheld_unknown(pack, s) for s in withheld),
            conditions=tuple(s.condition for s in withheld), **base,
        )
    missing = [
        key for key in sorted(reference.inputs)
        if key not in evaluator.irrelevant and not _known(supplied, key)
    ]
    if missing:
        return RuleAnswer(
            status="withheld", answer=None,
            unknowns=tuple(
                _input_unknown(example_id, key, "missing" if key not in supplied else "unknown") for key in missing
            ),
            **base,
        )
    outcome = evaluator.run(example_id, supplied, pack)
    rule_conditions = tuple(s.condition for s in statuses if s.condition)
    return RuleAnswer(
        status=outcome.status,
        answer=outcome.answer,
        unknowns=outcome.unknowns,
        conditions=outcome.conditions + rule_conditions,
        scope_notes=outcome.scope_notes,
        **base,
    )


# ---------------------------------------------------------------------------
# Arithmetic bounds the examples rest on
# ---------------------------------------------------------------------------

_POOL_SPANS = {
    "S-3": ("form_s3.I.B.6", ("form_s3:I.B.6", "form_s3:I.B.6.instructions")),
    "F-3": ("form_f3.I.B.5", ("form_f3:I.B.5", "form_f3:I.B.5.instructions")),
}


def _require_usd(quantity: Any, name: str) -> Quantity:
    _require(isinstance(quantity, Quantity), f"{name}: Quantity required")
    _require(quantity.unit == "usd", f"{name}: unit {quantity.unit!r} is not usd (A20)")
    return quantity


def baby_shelf_limit(public_float: Quantity, *, form: str = "S-3") -> Quantity:
    """One-third limit of I.B.6 (S-3) or I.B.5 (F-3) from a dollar public float.

    An unknown float gives an unknown limit, never zero or unlimited. A float of
    $75 million or more makes the limit not applicable (Instruction 3).
    """
    _require(form in _POOL_SPANS, f"form {form!r}: only S-3 or F-3")
    _require_usd(public_float, "public_float")
    rule_id = _POOL_SPANS[form][0]
    if public_float.status != "known":
        return Quantity(
            unit="usd", status=public_float.status,
            note=f"{rule_id}: the public float is {public_float.status}, so the one-third limit is too",
        )
    value = public_float.decimal
    if value >= BABY_SHELF_FLOAT_THRESHOLD_USD:
        return Quantity(
            unit="usd", status="not_applicable",
            note=f"{rule_id}: public float of $75 million or more; the one-third limit does not apply",
        )
    third = (value / 3).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return Quantity.known(format(third, "f"), "usd", applicability=f"{rule_id}(a): public float below $75 million")


def _twelve_month_window(sale_date: str) -> tuple[str, str]:
    sale = date.fromisoformat(sale_date)
    year = sale.year - 1
    day = min(sale.day, calendar.monthrange(year, sale.month)[1])
    start = date(year, sale.month, day) + timedelta(days=1)
    return start.isoformat(), sale.isoformat()


@dataclass(frozen=True)
class BabyShelfPool:
    """The I.B.6/I.B.5 one-third pool on one sale date, with exact headroom.

    ``headroom`` and ``overrun`` are both nonnegative; at most one is positive.
    Either is unknown whenever the limit or the trailing sales are unknown.
    """

    constraint: Constraint
    sold_trailing: Quantity
    headroom: Quantity
    overrun: Quantity
    float_measured_on: str | None

    def as_record(self) -> dict[str, Any]:
        record = _record({item.name: getattr(self, item.name) for item in fields(self)})
        _walk_keys(record, "baby_shelf_pool")
        return record


def baby_shelf_pool(
    pack: RuleApplicabilityPack,
    *,
    public_float: Quantity,
    float_measured_on: str | None,
    sold_trailing: Quantity,
    sold_window: tuple[str, str],
    sale_date: str,
    form: str = "S-3",
) -> BabyShelfPool:
    """Compare trailing-12-month I.B.6/I.B.5 sales with the one-third limit.

    ``sold_window`` must be exactly the 12 calendar months ending on and
    including ``sale_date``; a different interval is refused rather than
    compared (A20). A float measured outside the 60 days before the sale
    (Instruction 1) leaves the limit unknown.
    """
    _iso(sale_date, "sale_date")
    _require(form in _POOL_SPANS, f"form {form!r}: only S-3 or F-3")
    _require_usd(sold_trailing, "sold_trailing")
    window = _twelve_month_window(sale_date)
    _require(tuple(sold_window) == window, f"sold_window {tuple(sold_window)} is not the I.B.6 window {window} (A20)")
    rule_id, span_ids = _POOL_SPANS[form]
    _require(rule_status_as_of(pack, rule_id, sale_date).state != "not_in_force", f"{rule_id} not in force on {sale_date}")
    limit = baby_shelf_limit(public_float, form=form)
    if limit.status == "known":
        measured_ok = float_measured_on is not None and (
            date.fromisoformat(sale_date) - timedelta(days=FLOAT_MEASUREMENT_LOOKBACK_DAYS)
            <= date.fromisoformat(_iso(float_measured_on, "float_measured_on"))
            <= date.fromisoformat(sale_date)
        )
        if not measured_ok:
            limit = Quantity.unknown(
                "usd", note=f"{rule_id} Instruction 1: float not measured within 60 days before the sale on {sale_date}"
            )
    evidence = tuple(EvidenceRef(EVIDENCE_MANIFEST_ID, span_id, pack.span(span_id).sha256) for span_id in span_ids)
    applicability = f"{rule_id}(a): sales under the instruction in the 12 calendar months ending {sale_date}"
    if limit.status == "not_applicable":
        status = "inapplicable"
        headroom = overrun = Quantity(unit="usd", status="not_applicable")
    elif limit.status != "known" or sold_trailing.status != "known":
        status, headroom, overrun = "unknown", Quantity.unknown("usd"), Quantity.unknown("usd")
    else:
        gap = limit.decimal - sold_trailing.decimal
        status = "slack" if gap > 0 else "binding"
        zero = Decimal(0)
        headroom = Quantity.known(format(gap if gap > 0 else zero, "f"), "usd", applicability=applicability)
        overrun = Quantity.known(format(-gap if gap < 0 else zero, "f"), "usd", applicability=applicability)
    constraint = Constraint(
        constraint_id=stable_id("constraint", {"rule": rule_id, "sale_date": sale_date, "limit": limit.as_record()}),
        kind="dollars",
        bound=limit,
        status=status,
        stock_or_flow="flow",
        applicability=applicability,
        evidence=evidence,
        window_start=window[0],
        window_end=window[1],
    )
    return BabyShelfPool(constraint, sold_trailing, headroom, overrun, float_measured_on)


@dataclass(frozen=True)
class TwentyPercentTest:
    """Nasdaq 5635(d) share-count test on the 5635(e)(1) outstanding basis.

    ``approval_required`` is ``None`` when the price leg is unknown: unknown
    never becomes ``False``. Only Rule 5635(d) is tested (A14).
    """

    threshold: Quantity
    largest_issuance_below_threshold: Quantity
    proposed: Quantity
    is_twenty_percent_issuance: bool | None
    approval_required: bool | None
    scope_notes: tuple[str, ...] = field(default=())

    def as_record(self) -> dict[str, Any]:
        record = _record({item.name: getattr(self, item.name) for item in fields(self)})
        _walk_keys(record, "twenty_percent_test")
        return record


def nasdaq_twenty_percent(
    *,
    outstanding: Quantity,
    proposed: Quantity,
    price_relative_to_minimum_price: str,
) -> TwentyPercentTest:
    """Smallest 20% Issuance and whether 5635(d)(2) approval is required.

    ``outstanding`` must be issued-and-outstanding shares (treasury, subsidiary
    and reserved shares do not count, 5635(e)(1)); ``proposed`` must be a
    scenario issuance in the same unit. The voting-power prong needs vote
    counts and is not computed here.
    """
    for name, quantity, basis in (
        ("outstanding", outstanding, "issued_and_outstanding"),
        ("proposed", proposed, "scenario_incremental_issuance"),
    ):
        _require(isinstance(quantity, Quantity), f"{name}: Quantity required")
        _require(quantity.unit == "shares", f"{name}: unit {quantity.unit!r} is not shares (A20)")
        _require(quantity.share_basis == basis, f"{name}: share basis {quantity.share_basis!r} is not {basis} (A20)")
    _require(
        price_relative_to_minimum_price in ("below", "at_or_above", _UNKNOWN),
        f"price_relative_to_minimum_price {price_relative_to_minimum_price!r}",
    )
    notes = ("only Rule 5635(d) is tested; the voting-power prong and Rules 5635(a)-(c) are not (A14)",)
    if outstanding.status != "known":
        unknown = Quantity.unknown("shares", share_basis="issued_and_outstanding")
        return TwentyPercentTest(unknown, unknown, proposed, None, None, notes)
    threshold = (outstanding.decimal * NASDAQ_TWENTY_PERCENT).to_integral_value(rounding=ROUND_CEILING)
    applicability = "nasdaq.5635.d.1.B: 20% of shares outstanding before the issuance"
    threshold_q = Quantity.known(format(threshold, "f"), "shares", share_basis="issued_and_outstanding", applicability=applicability)
    below_q = Quantity.known(
        format(max(threshold - 1, Decimal(0)), "f"), "shares", share_basis="issued_and_outstanding", applicability=applicability
    )
    if proposed.status != "known":
        return TwentyPercentTest(threshold_q, below_q, proposed, None, None, notes)
    is_twenty = proposed.decimal >= threshold
    if price_relative_to_minimum_price == _UNKNOWN:
        required = None if is_twenty else False
    else:
        required = is_twenty and price_relative_to_minimum_price == "below"
    return TwentyPercentTest(threshold_q, below_q, proposed, is_twenty, required, notes)


def gap_report(pack: RuleApplicabilityPack) -> dict[str, list[str]]:
    """Open and closed gaps by owner, as recorded in the pack."""
    report: dict[str, list[str]] = {}
    for gap_id, gap in sorted(pack.gaps.items()):
        report.setdefault(gap.get("status", "inherited"), []).append(gap_id)
    return report


__all__: Sequence[str] = (
    "ANSWER_STATUSES",
    "BABY_SHELF_FLOAT_THRESHOLD_USD",
    "EVIDENCE_MANIFEST_ID",
    "EXCLUDED_PROPOSALS",
    "RULE_APPLICABILITY_PACK_RELPATH",
    "RULE_APPLICABILITY_PACK_SCHEMA",
    "RULE_APPLICABILITY_PACK_VERSION",
    "RULE_STATES",
    "ApplicableRule",
    "BabyShelfPool",
    "PackExample",
    "RuleAnswer",
    "RuleApplicabilityError",
    "RuleApplicabilityPack",
    "RuleSpan",
    "RuleStatus",
    "RuleWindow",
    "TwentyPercentTest",
    "baby_shelf_limit",
    "baby_shelf_pool",
    "build_rule_pack",
    "evaluate_example",
    "gap_report",
    "load_rule_applicability_pack",
    "nasdaq_twenty_percent",
    "normalized_digest",
    "parse_rule_applicability_pack",
    "rule_status_as_of",
)
