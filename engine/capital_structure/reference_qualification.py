"""Reference qualification pack for Capital Structure Intelligence V2 (task E0).

E0 qualifies the exact reference documents, source policy, rights, identities
and labelled gold that the later rule-applicability (L0), extraction (T0) and
reconciliation waves consume. It mints no facts: every entry points at bytes
the research seat retrieved once, hashed, and either committed as an exact span
(public-domain SEC text, or a Nasdaq excerpt inside the 500 character cap) or
kept as a digest-only receipt.

The pack itself is a config artifact, ``config/capital_structure_reference_pack.v1.json``.
This module reads and validates it. It never fetches, never writes under
``data/`` and never widens the SEC request budget: requalification is a
documented manual procedure carried inside the pack, not a collector.

Acceptance rows pinned here (masterplan §15): A07 (gold references bind exact
issuer/security, document, span, date and allowed source; old ticker/sector
labels are not silently reused) and A09 (LLM-proposed spans or interpretations
cannot mint canonical facts without the accepted extraction/adjudication
procedure).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

REFERENCE_PACK_SCHEMA = "capital_structure.reference_pack.v1"
REFERENCE_PACK_VERSION = "capital-structure-reference-qualification/1.1.0"
REFERENCE_PACK_RELPATH = Path("config") / "capital_structure_reference_pack.v1.json"
REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCE_CLASSES = frozenset({
    "binding_rule",
    "staff_interpretation",
    "exchange_rule",
    "proposed_reform",
    "rulemaking_index",
    "operational_policy",
    "identity_registry",
})
# Classes whose text may feed a rule-applicability test. Each keeps its own
# authority kind: a staff interpretation is guidance with an interpretation
# date, never a Commission rule.
RULE_AUTHORITY_CLASSES = frozenset({"binding_rule", "exchange_rule", "staff_interpretation"})
# Classes that may be enforceable (binding on an issuer in the venue).
ENFORCEABLE_CLASSES = frozenset({"binding_rule", "exchange_rule"})
# Classes that can never be enforced or used as a rule source.
NEVER_RULE_CLASSES = frozenset(SOURCE_CLASSES - RULE_AUTHORITY_CLASSES)
QUALIFICATIONS = frozenset({"qualified", "browser_qualified", "blocked", "unqualified"})
CANONICAL_FACT_ORIGINS = frozenset({"canonical_extraction", "adjudicated_gold"})
NON_CANONICAL_FACT_ORIGINS = frozenset({
    "llm_proposed_span", "llm_interpretation", "issuer_assertion", "model_prose",
})
EXCERPT_CAP_CHARS = 500
GOLD_FIXTURE_PREFIX = "tests/fixtures/capital_structure/"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CIK = re.compile(r"^\d{10}$")


class ReferencePackError(ValueError):
    """The reference pack is malformed or violates an E0 invariant."""


def span_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_label(label: str) -> str:
    """Casefold and strip punctuation so 'AAR CORP' and 'AAR Corp.' compare equal."""
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", label.casefold()).split())


def fact_origin_is_canonical(origin: str) -> bool:
    """Only canonical extraction and adjudicated gold may mint a fact (A09)."""
    return origin in CANONICAL_FACT_ORIGINS


@dataclass(frozen=True)
class QualifiedSpan:
    label: str
    text: str
    chars: int
    sha256: str
    interpretation_date: str | None
    details: Mapping[str, Any]


@dataclass(frozen=True)
class QualifiedSource:
    source_id: str
    source_class: str
    qualification: str
    url: str
    title: str
    publisher: str
    jurisdiction: str
    edition_label: str
    edition_date: str | None
    rights: str
    enforceable: bool
    reason: str
    retrieved_at: str
    http_status: int | None
    bytes: int | None
    sha256: str
    spans: tuple[QualifiedSpan, ...]
    details: Mapping[str, Any]

    @property
    def is_rule_authority(self) -> bool:
        return self.source_class in RULE_AUTHORITY_CLASSES

    def span(self, label: str) -> QualifiedSpan:
        for item in self.spans:
            if item.label == label:
                return item
        raise KeyError(label)


@dataclass(frozen=True)
class RuleExample:
    example_id: str
    source_id: str
    span_label: str
    interpretation_date: str
    negative: bool
    rule_refs: tuple[str, ...]
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]


@dataclass(frozen=True)
class IdentityBinding:
    archetype: str
    ticker: str
    ticker_as_of: str
    cik: str
    issuer_id: str
    registry_name: str
    submissions_name: str
    prior_label: str
    prior_reference: Mapping[str, Any]
    label_drift: bool
    former_names: tuple[Mapping[str, Any], ...]
    exchanges: tuple[str, ...]
    qualification: str
    reason: str
    source_ids: tuple[str, ...]
    case_supply: str
    case_supply_reason: str
    replacement: Mapping[str, Any] | None
    replacement_owed: bool
    details: Mapping[str, Any]

    @property
    def current_label(self) -> str:
        return self.registry_name


@dataclass(frozen=True)
class GoldCase:
    gold_id: str
    path: str
    sha256: str
    bytes: int
    provenance: str
    allowed_source: str
    consumers: tuple[str, ...]
    expectations: tuple[Mapping[str, Any], ...]
    details: Mapping[str, Any]


@dataclass(frozen=True)
class ReferencePack:
    schema: str
    version: str
    task: str
    qualified_on: str
    acceptance_rows: tuple[str, ...]
    masterplan: Mapping[str, Any]
    request_policy: Mapping[str, Any]
    fact_origins: Mapping[str, bool]
    sources: tuple[QualifiedSource, ...]
    rule_examples: tuple[RuleExample, ...]
    identities: tuple[IdentityBinding, ...]
    gold_cases: tuple[GoldCase, ...]
    source_policy: Mapping[str, Any]
    rights: Mapping[str, Any]
    gaps: tuple[Mapping[str, Any], ...]
    requalification_procedure: Mapping[str, Any]

    def source(self, source_id: str) -> QualifiedSource:
        for item in self.sources:
            if item.source_id == source_id:
                return item
        raise KeyError(source_id)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReferencePackError(message)


def _rest(raw: Mapping[str, Any], used: Sequence[str]) -> Mapping[str, Any]:
    return {k: v for k, v in raw.items() if k not in set(used)}


_SPAN_KEYS = ("label", "text", "chars", "sha256", "interpretation_date")
_SOURCE_KEYS = (
    "source_id", "source_class", "qualification", "url", "title", "publisher", "jurisdiction",
    "edition_label", "edition_date", "rights", "enforceable", "reason", "retrieved_at",
    "http_status", "bytes", "sha256", "spans",
)
_IDENTITY_KEYS = (
    "archetype", "ticker", "ticker_as_of", "cik", "issuer_id", "registry_name", "submissions_name",
    "prior_label", "prior_reference", "label_drift", "former_names", "exchanges", "qualification",
    "reason", "source_ids", "case_supply", "case_supply_reason", "replacement", "replacement_owed",
)
_GOLD_KEYS = ("gold_id", "path", "sha256", "bytes", "provenance", "allowed_source", "consumers", "expectations")


def _span(raw: Mapping[str, Any], source: Mapping[str, Any]) -> QualifiedSpan:
    text = raw["text"]
    _require(isinstance(text, str) and text.strip() != "", f"empty span text in {source['source_id']}")
    _require(raw["chars"] == len(text), f"span {raw['label']}: chars does not match text length")
    _require(raw["sha256"] == span_digest(text), f"span {raw['label']}: sha256 does not match text")
    date = raw.get("interpretation_date")
    _require(date is None or bool(_ISO_DATE.match(date)), f"span {raw['label']}: interpretation_date not ISO")
    if source.get("rights") == "excerpt_limited":
        _require(len(text) <= EXCERPT_CAP_CHARS,
                 f"span {raw['label']}: {len(text)} chars exceeds the {EXCERPT_CAP_CHARS} char excerpt cap")
    return QualifiedSpan(label=raw["label"], text=text, chars=raw["chars"], sha256=raw["sha256"],
                         interpretation_date=date, details=_rest(raw, _SPAN_KEYS))


def _source(raw: Mapping[str, Any]) -> QualifiedSource:
    sid = raw["source_id"]
    _require(raw["source_class"] in SOURCE_CLASSES, f"{sid}: unknown source_class {raw['source_class']!r}")
    _require(raw["qualification"] in QUALIFICATIONS, f"{sid}: unknown qualification {raw['qualification']!r}")
    _require(bool(_HEX64.match(raw["sha256"])), f"{sid}: sha256 is not a lowercase hex digest")
    _require(isinstance(raw["retrieved_at"], str) and raw["retrieved_at"].startswith("20"), f"{sid}: retrieved_at missing")
    _require(isinstance(raw["enforceable"], bool), f"{sid}: enforceable must be a bool")
    _require(isinstance(raw["reason"], str) and raw["reason"].strip() != "", f"{sid}: reason is required")
    if raw["source_class"] in NEVER_RULE_CLASSES:
        _require(raw["enforceable"] is False, f"{sid}: {raw['source_class']} can never be enforceable")
    if raw["source_class"] == "proposed_reform":
        _require(raw.get("status") == "proposed", f"{sid}: proposed_reform must carry status 'proposed'")
        _require(raw.get("final_rule_evidence") is None,
                 f"{sid}: a proposed reform with final-rule evidence must be requalified, not kept proposed")
    if raw["qualification"] == "browser_qualified":
        rendered = raw.get("rendered_receipt") or {}
        _require(bool(_HEX64.match(str(rendered.get("page_text_sha256", "")))),
                 f"{sid}: browser_qualified needs a rendered_receipt.page_text_sha256")
        _require(raw["sha256"] == rendered["page_text_sha256"],
                 f"{sid}: browser_qualified sha256 must be the rendered page digest")
        fetched = raw.get("fetch_receipt") or {}
        _require(fetched.get("http_status") not in (None, 200),
                 f"{sid}: browser_qualified must keep the refused non-browser fetch receipt")
    if raw["qualification"] in ("blocked", "unqualified"):
        _require(not raw.get("spans"), f"{sid}: a {raw['qualification']} source may not carry spans")
    spans = tuple(_span(s, raw) for s in raw.get("spans", []))
    return QualifiedSource(
        source_id=sid, source_class=raw["source_class"], qualification=raw["qualification"], url=raw["url"],
        title=raw["title"], publisher=raw["publisher"], jurisdiction=raw["jurisdiction"],
        edition_label=raw["edition_label"], edition_date=raw.get("edition_date"), rights=raw["rights"],
        enforceable=raw["enforceable"], reason=raw["reason"], retrieved_at=raw["retrieved_at"],
        http_status=raw.get("http_status"), bytes=raw.get("bytes"), sha256=raw["sha256"], spans=spans,
        details=_rest(raw, _SOURCE_KEYS),
    )


def _example(raw: Mapping[str, Any], sources: Mapping[str, QualifiedSource]) -> RuleExample:
    eid = raw["example_id"]
    _require(raw["source_id"] in sources, f"{eid}: unknown source_id {raw['source_id']!r}")
    source = sources[raw["source_id"]]
    _require(source.is_rule_authority, f"{eid}: source class {source.source_class} may not supply a rule example")
    _require(source.qualification in ("qualified", "browser_qualified"),
             f"{eid}: source {source.source_id} is {source.qualification}")
    try:
        span = source.span(raw["span_label"])
    except KeyError:
        raise ReferencePackError(f"{eid}: span {raw['span_label']!r} is not in {source.source_id}") from None
    _require(bool(_ISO_DATE.match(raw["interpretation_date"])), f"{eid}: interpretation_date not ISO")
    if span.interpretation_date is not None:
        _require(span.interpretation_date == raw["interpretation_date"],
                 f"{eid}: interpretation_date disagrees with its span")
    _require(isinstance(raw["negative"], bool), f"{eid}: negative must be a bool")
    _require(bool(raw["rule_refs"]), f"{eid}: rule_refs is required")
    _require(bool(raw["inputs"]) and bool(raw["expected"]), f"{eid}: inputs and expected are required")
    return RuleExample(example_id=eid, source_id=raw["source_id"], span_label=raw["span_label"],
                       interpretation_date=raw["interpretation_date"], negative=raw["negative"],
                       rule_refs=tuple(raw["rule_refs"]), inputs=dict(raw["inputs"]), expected=dict(raw["expected"]))


def _identity(raw: Mapping[str, Any], sources: Mapping[str, QualifiedSource]) -> IdentityBinding:
    arch = raw["archetype"]
    _require(bool(_CIK.match(raw["cik"])), f"{arch}: cik must be ten digits")
    _require(raw["issuer_id"] == f"sec:cik:{raw['cik']}", f"{arch}: issuer_id must be sec:cik:<cik>")
    _require(raw["qualification"] in QUALIFICATIONS, f"{arch}: unknown qualification")
    _require(bool(raw["source_ids"]), f"{arch}: an identity needs at least one registry source")
    for sid in raw["source_ids"]:
        _require(sid in sources, f"{arch}: unknown source_id {sid!r}")
        _require(sources[sid].source_class == "identity_registry", f"{arch}: {sid} is not an identity registry")
    _require(isinstance(raw["label_drift"], bool), f"{arch}: label_drift must be a bool")
    drift_observed = not normalize_label(raw["registry_name"]).startswith(normalize_label(raw["prior_label"]))
    _require(raw["label_drift"] == drift_observed,
             f"{arch}: label_drift flag disagrees with registry_name vs prior_label")
    if raw["label_drift"]:
        former = {normalize_label(n["name"]) for n in raw["former_names"]}
        _require(normalize_label(raw["prior_label"]) in former,
                 f"{arch}: a drifted prior label must be witnessed by formerNames")
        _require("former" in raw["reason"].casefold(), f"{arch}: a drifted identity must explain the former name")
    _require(raw["case_supply"] in ("supplied", "unsupplied"), f"{arch}: unknown case_supply")
    if raw["case_supply"] == "unsupplied":
        _require(raw["replacement_owed"] is True, f"{arch}: an unsupplied archetype owes a replacement")
        rep = raw.get("replacement")
        _require(rep is None or bool(rep.get("source_ids")),
                 f"{arch}: a replacement issuer must bind registry sources; it may not be guessed")
    else:
        _require(raw["replacement_owed"] is False, f"{arch}: a supplied archetype owes no replacement")
    return IdentityBinding(
        archetype=arch, ticker=raw["ticker"], ticker_as_of=raw["ticker_as_of"], cik=raw["cik"],
        issuer_id=raw["issuer_id"], registry_name=raw["registry_name"], submissions_name=raw["submissions_name"],
        prior_label=raw["prior_label"], prior_reference=dict(raw["prior_reference"]), label_drift=raw["label_drift"],
        former_names=tuple(dict(n) for n in raw["former_names"]), exchanges=tuple(raw["exchanges"]),
        qualification=raw["qualification"], reason=raw["reason"], source_ids=tuple(raw["source_ids"]),
        case_supply=raw["case_supply"], case_supply_reason=raw["case_supply_reason"],
        replacement=raw.get("replacement"), replacement_owed=raw["replacement_owed"],
        details=_rest(raw, _IDENTITY_KEYS),
    )


def _gold(raw: Mapping[str, Any]) -> GoldCase:
    gid = raw["gold_id"]
    _require(raw["path"].startswith(GOLD_FIXTURE_PREFIX), f"{gid}: gold must live under {GOLD_FIXTURE_PREFIX}")
    _require(bool(_HEX64.match(raw["sha256"])), f"{gid}: sha256 is not a lowercase hex digest")
    _require(bool(raw["consumers"]), f"{gid}: gold without a consuming test is not gold")
    _require(bool(raw["expectations"]), f"{gid}: gold needs at least one labelled expectation")
    for exp in raw["expectations"]:
        _require(bool(exp.get("test")) and bool(exp.get("claim")), f"{gid}: expectation needs test and claim")
    return GoldCase(gold_id=gid, path=raw["path"], sha256=raw["sha256"], bytes=raw["bytes"],
                    provenance=raw["provenance"], allowed_source=raw["allowed_source"],
                    consumers=tuple(raw["consumers"]), expectations=tuple(dict(e) for e in raw["expectations"]),
                    details=_rest(raw, _GOLD_KEYS))


def parse_reference_pack(raw: Mapping[str, Any]) -> ReferencePack:
    _require(raw.get("schema") == REFERENCE_PACK_SCHEMA, f"schema must be {REFERENCE_PACK_SCHEMA}")
    _require(raw.get("version") == REFERENCE_PACK_VERSION, f"version must be {REFERENCE_PACK_VERSION}")
    sources = tuple(_source(s) for s in raw["sources"])
    by_id = {s.source_id: s for s in sources}
    _require(len(by_id) == len(sources), "duplicate source_id")
    labels = [sp.label for s in sources for sp in s.spans]
    _require(len(labels) == len(set(labels)), "duplicate span label across sources")
    examples = tuple(_example(e, by_id) for e in raw["rule_examples"])
    _require(len({e.example_id for e in examples}) == len(examples), "duplicate example_id")
    identities = tuple(_identity(i, by_id) for i in raw["identities"])
    _require(len({i.archetype for i in identities}) == len(identities), "duplicate archetype")
    gold = tuple(_gold(g) for g in raw["gold_cases"])
    _require(len({g.gold_id for g in gold}) == len(gold), "duplicate gold_id")
    origins = dict(raw["fact_origins"])
    for origin in CANONICAL_FACT_ORIGINS:
        _require(origins.get(origin) is True, f"fact_origins.{origin} must be true")
    for origin in NON_CANONICAL_FACT_ORIGINS:
        _require(origins.get(origin) is False, f"fact_origins.{origin} must be false")
    policy = dict(raw["source_policy"])
    _require(policy.get("reserves_changed_by_e0") is False, "E0 may not change the request class reserves")
    _require(policy.get("collector_added_by_e0") is False, "E0 may not add a collector")
    procedure = dict(raw["requalification_procedure"])
    _require(bool(procedure.get("steps")), "requalification_procedure.steps is required")
    return ReferencePack(
        schema=raw["schema"], version=raw["version"], task=raw["task"], qualified_on=raw["qualified_on"],
        acceptance_rows=tuple(raw["acceptance_rows"]), masterplan=dict(raw["masterplan"]),
        request_policy=dict(raw["request_policy"]), fact_origins=origins, sources=sources,
        rule_examples=examples, identities=identities, gold_cases=gold, source_policy=policy,
        rights=dict(raw["rights"]), gaps=tuple(dict(g) for g in raw["gaps"]), requalification_procedure=procedure,
    )


def load_reference_pack(path: Path | None = None) -> ReferencePack:
    target = path if path is not None else REPO_ROOT / REFERENCE_PACK_RELPATH
    with open(target, encoding="utf-8") as fh:
        raw = json.load(fh)
    return parse_reference_pack(raw)


def verify_gold_fixtures(pack: ReferencePack, root: Path | None = None) -> dict[str, str]:
    """Return gold_id -> problem for every gold whose bytes no longer match; empty means verified."""
    base = root if root is not None else REPO_ROOT
    problems: dict[str, str] = {}
    for gold in pack.gold_cases:
        path = base / gold.path
        if not path.is_file():
            problems[gold.gold_id] = "missing"
            continue
        actual = file_digest(path)
        if actual != gold.sha256:
            problems[gold.gold_id] = f"sha256 mismatch: {actual}"
    return problems


def enforceable_sources(pack: ReferencePack) -> tuple[QualifiedSource, ...]:
    return tuple(s for s in pack.sources if s.enforceable and s.source_class in ENFORCEABLE_CLASSES)


def rule_sources(pack: ReferencePack) -> tuple[QualifiedSource, ...]:
    """Sources whose spans may feed a rule-applicability test; proposed reforms are never here."""
    return tuple(s for s in pack.sources
                 if s.is_rule_authority and s.qualification in ("qualified", "browser_qualified"))


def identity_for(pack: ReferencePack, archetype: str) -> IdentityBinding:
    for item in pack.identities:
        if item.archetype == archetype:
            return item
    raise KeyError(archetype)


def rule_examples(pack: ReferencePack, source_id: str | None = None) -> tuple[RuleExample, ...]:
    return tuple(e for e in pack.rule_examples if source_id is None or e.source_id == source_id)


def qualification_report(pack: ReferencePack, root: Path | None = None) -> dict[str, Any]:
    gold_problems = verify_gold_fixtures(pack, root)
    return {
        "schema": pack.schema,
        "version": pack.version,
        "qualified_on": pack.qualified_on,
        "sources": {q: sum(1 for s in pack.sources if s.qualification == q) for q in sorted(QUALIFICATIONS)},
        "source_classes": {c: sum(1 for s in pack.sources if s.source_class == c) for c in sorted(SOURCE_CLASSES)},
        "enforceable_source_ids": [s.source_id for s in enforceable_sources(pack)],
        "rule_examples": len(pack.rule_examples),
        "negative_examples": sum(1 for e in pack.rule_examples if e.negative),
        "identities": {i.archetype: {"cik": i.cik, "label_drift": i.label_drift, "case_supply": i.case_supply}
                       for i in pack.identities},
        "gold_cases": len(pack.gold_cases),
        "gold_problems": gold_problems,
        "gaps": [g["gap_id"] for g in pack.gaps],
    }


__all__ = [
    "CANONICAL_FACT_ORIGINS", "ENFORCEABLE_CLASSES", "EXCERPT_CAP_CHARS", "GOLD_FIXTURE_PREFIX",
    "GoldCase", "IdentityBinding", "NEVER_RULE_CLASSES", "NON_CANONICAL_FACT_ORIGINS", "QUALIFICATIONS",
    "QualifiedSource", "QualifiedSpan", "REFERENCE_PACK_RELPATH", "REFERENCE_PACK_SCHEMA",
    "REFERENCE_PACK_VERSION", "RULE_AUTHORITY_CLASSES", "ReferencePack", "ReferencePackError",
    "RuleExample", "SOURCE_CLASSES", "enforceable_sources", "fact_origin_is_canonical", "file_digest",
    "identity_for", "load_reference_pack", "normalize_label", "parse_reference_pack",
    "qualification_report", "rule_examples", "rule_sources", "span_digest", "verify_gold_fixtures",
]
