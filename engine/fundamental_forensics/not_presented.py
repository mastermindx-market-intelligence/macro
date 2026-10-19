"""Governed not-presented (NP) evidence for core GAAP item metrics.

An NP verdict states one narrow, checkable fact about one filing: the filer's
own calculation linkbase decomposes the slot's parent total exactly, using
standard children only, and none of the calculation tree, the statement
presentation tree, or the filed facts in the slot context carries the
metric's concept family. The verdict never carries a value. It is the evidence
a query engine needs before it may print ``NOT_APPLICABLE`` with reason
``not_presented`` instead of ``MISSING``. Absent stays absent whenever any
check fails, whenever a linkbase is missing or unparseable, and whenever the
rule pack is not yet visible at the query's ``recorded_at``.

The rule pack is a governed, content-digested YAML document
(``config/fundamental_forensics/metrics/v1/not_presented/core.yaml``). This
module loads it fail-closed, evaluates one metric against parsed linkbases and
an exact slot-context fact map, and can recompute the evidence from package
bytes (``verify_not_presented_evidence``; the engine entry point is
``BitemporalMetricQueryEngine.verify_not_presented``).

That recomputation is available but is NOT on the receipt replay path yet:
``MetricMatrix.from_dict`` / ``MetricCell.from_dict`` replay checks only the
evidence shape and the NP rule-id prefix, so a receipt whose evidence was
altered but stays well-formed replays. A caller that needs the verdict
re-proven must hold the filing packages and call the verifier explicitly.
The whole NP path is dormant until a caller constructs the engine with
``not_presented_pack=`` and ``filing_packages=``; no production query path
does so today.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

from .metric_registry import (
    ImmutableRule,
    _exact_keys,
    _identifier,
    _load_yaml,
    _require_list,
    _require_mapping,
    _rule,
    _text,
    _utc,
    _verify_content_digest,
    _version,
)
from .statement_graph import (
    LINK,
    StatementGraphError,
    _local_name,
    _parse_xml,
    _xlink,
    concept_from_href,
)

NOT_PRESENTED_SCHEMA = "fundamental_forensics.not_presented_rules/v1"
CORE_NOT_PRESENTED_PACK_ID = "fundamental_forensics_core_not_presented"
NA_BASIS_NOT_PRESENTED_ITEM = "not_presented_item"
NP_KIND_ITEM = "item_not_in_composition"
NOT_PRESENTED_REASON = "not_presented"
OUTCOME_NOT_PRESENTED = "not_presented"
OUTCOME_ABSENT = "absent"
FOOTING_EXACT = "exact"
FOOTING_OFF = "off"

DEFAULT_NOT_PRESENTED_PACK_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "fundamental_forensics"
    / "metrics"
    / "v1"
    / "not_presented"
    / "core.yaml"
)

# Census reason order, plus one kernel-only reason (a package without a
# presentation member cannot run the statement guard, so it stays absent).
REASON_ORDER: tuple[str, ...] = (
    "np_no_rule",
    "np_no_calc_linkbase",
    "np_no_presentation_linkbase",
    "np_parse_error",
    "np_no_parent",
    "np_extension_child",
    "np_family_in_calc",
    "np_container_leaf",
    "np_children_no_facts",
    "np_unbalanced",
    "np_family_in_statement_pre",
    "np_family_fact",
)

_ALLOWED_NA_BASIS = frozenset({NA_BASIS_NOT_PRESENTED_ITEM})
_ALLOWED_NP_KINDS = frozenset({NP_KIND_ITEM})
_QNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*:[A-Za-z_][A-Za-z0-9_.-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_OFF_UNITS_EXPONENT = 18


class NotPresentedError(ValueError):
    """A not-presented pack, linkbase or evidence object failed closed."""


@dataclass(frozen=True)
class NotPresentedRule:
    """One governed item rule: which totals may decompose the metric away."""

    metric_id: str
    rule: ImmutableRule
    np_kind: str
    parent_tiers: tuple[tuple[str, ...], ...]
    family_pattern: str
    containers: str | None
    family_re: re.Pattern[str]
    containers_re: re.Pattern[str] | None


@dataclass(frozen=True)
class NotPresentedPack:
    pack_id: str
    pack_version: str
    available_at: datetime
    na_basis: str
    child_taxonomy_prefix: str
    pre_role_exclude: str
    pre_ignore_suffix: str
    source_rules_sha256: str
    content_sha256: str
    rules: Mapping[str, NotPresentedRule]
    pre_role_exclude_re: re.Pattern[str]
    pre_ignore_suffix_re: re.Pattern[str]

    def visible_rule(self, metric_id: str, *, recorded_at: datetime) -> NotPresentedRule | None:
        """The rule for ``metric_id`` only when pack and rule were visible at ``recorded_at``."""
        rule = self.rules.get(metric_id)
        if rule is None:
            return None
        if self.available_at > recorded_at or rule.rule.available_at > recorded_at:
            return None
        return rule


@dataclass(frozen=True)
class CalculationNetworks:
    """Per calculationLink element (document order): parent -> ((child, weight), ...)."""

    links: tuple[tuple[str, Mapping[str, tuple[tuple[str, Decimal], ...]]], ...]

    def parents(self) -> frozenset[str]:
        return frozenset(parent for _role, by_parent in self.links for parent in by_parent)

    def children_by_link(self, parent: str) -> tuple[tuple[int, tuple[tuple[str, Decimal], ...]], ...]:
        return tuple(
            (index, by_parent[parent])
            for index, (_role, by_parent) in enumerate(self.links)
            if parent in by_parent
        )


@dataclass(frozen=True)
class PresentationNetworks:
    """Per presentationLink element (document order): (role, concept local names)."""

    links: tuple[tuple[str, frozenset[str]], ...]


@dataclass(frozen=True)
class NotPresentedVerdict:
    """Evidence for one metric cell. Deliberately has no value field."""

    metric_id: str
    outcome: str
    reason: str | None
    fails: tuple[str, ...]
    np_kind: str | None
    na_basis: str | None
    rule_id: str | None
    rule_version: str | None
    rules_sha256: str
    parent_concepts: tuple[str, ...]
    roles_checked: int
    children_n: int
    children_with_fact_n: int
    footing: str | None
    off_units: int | None
    extension_children: tuple[str, ...]
    cal_sha256: str | None = None
    pre_sha256: str | None = None
    accession: str | None = None

    @property
    def is_not_presented(self) -> bool:
        return self.outcome == OUTCOME_NOT_PRESENTED

    def evidence(self) -> dict[str, Any]:
        """The flat provenance projection a NOT_APPLICABLE cell carries."""
        if not self.is_not_presented:
            raise NotPresentedError("only a not_presented verdict carries cell evidence")
        return {
            "na_basis": self.na_basis,
            "np_kind": self.np_kind,
            "np_rule_id": self.rule_id,
            "np_rule_version": self.rule_version,
            "np_rules_sha256": self.rules_sha256,
            "np_parent_concepts": list(self.parent_concepts),
            "np_roles_checked": self.roles_checked,
            "np_children_n": self.children_n,
            "np_children_with_fact_n": self.children_with_fact_n,
            "np_footing": self.footing,
            "np_cal_sha256": self.cal_sha256,
            "np_pre_sha256": self.pre_sha256,
            "np_accession": self.accession,
        }


# ---------------------------------------------------------------- loading --


def _regex(value: Any, *, field: str) -> tuple[str, re.Pattern[str]]:
    pattern = _text(value, field=field)
    try:
        return pattern, re.compile(pattern)
    except re.error as exc:
        raise NotPresentedError(f"{field} is not a valid regular expression: {exc}") from exc


def _parent_tiers(value: Any, *, field: str) -> tuple[tuple[str, ...], ...]:
    tiers: list[tuple[str, ...]] = []
    seen: set[str] = set()
    for tier_index, tier in enumerate(_require_list(value, field=field)):
        members = _require_list(tier, field=f"{field}[{tier_index}]")
        if not members:
            raise NotPresentedError(f"{field}[{tier_index}] must not be empty")
        out: list[str] = []
        for member in members:
            qname = _text(member, field=f"{field}[{tier_index}]")
            if not _QNAME.fullmatch(qname):
                raise NotPresentedError(f"{field}[{tier_index}] member is not a prefixed concept: {qname!r}")
            if qname in seen:
                raise NotPresentedError(f"{field} repeats concept {qname!r}")
            seen.add(qname)
            out.append(qname)
        tiers.append(tuple(out))
    if not tiers:
        raise NotPresentedError(f"{field} must name at least one tier")
    return tuple(tiers)


def _rule_from_raw(raw: Any, *, field: str, known_metric_ids: frozenset[str] | None) -> NotPresentedRule:
    item = _require_mapping(raw, field=field)
    _exact_keys(
        item,
        field=field,
        required=frozenset({"metric_id", "rule", "np_kind", "parent_tiers", "family_pattern", "containers"}),
    )
    metric_id = _identifier(item.get("metric_id"), field=f"{field}.metric_id")
    if known_metric_ids is not None and metric_id not in known_metric_ids:
        raise NotPresentedError(f"{field}.metric_id is not a catalog metric: {metric_id!r}")
    rule = _rule(item.get("rule"), field=f"{field}.rule")
    if not rule.rule_id.startswith(f"not_presented.{metric_id}/"):
        raise NotPresentedError(f"{field}.rule.rule_id must name not_presented.{metric_id}")
    np_kind = _text(item.get("np_kind"), field=f"{field}.np_kind")
    if np_kind not in _ALLOWED_NP_KINDS:
        raise NotPresentedError(f"{field}.np_kind must be one of {sorted(_ALLOWED_NP_KINDS)}")
    tiers = _parent_tiers(item.get("parent_tiers"), field=f"{field}.parent_tiers")
    family_pattern, family_re = _regex(item.get("family_pattern"), field=f"{field}.family_pattern")
    containers_raw = item.get("containers")
    containers: str | None = None
    containers_re: re.Pattern[str] | None = None
    if containers_raw is not None:
        containers, containers_re = _regex(containers_raw, field=f"{field}.containers")
    return NotPresentedRule(
        metric_id=metric_id,
        rule=rule,
        np_kind=np_kind,
        parent_tiers=tiers,
        family_pattern=family_pattern,
        containers=containers,
        family_re=family_re,
        containers_re=containers_re,
    )


def not_presented_pack_from_dict(
    raw: Mapping[str, Any],
    *,
    known_metric_ids: Iterable[str] | None = None,
) -> NotPresentedPack:
    """Validate a parsed pack. Any unknown field, bad regex or digest drift raises."""
    pack = _require_mapping(raw, field="not_presented")
    _exact_keys(
        pack,
        field="not_presented",
        required=frozenset(
            {
                "schema",
                "pack_id",
                "pack_version",
                "available_at",
                "na_basis",
                "child_taxonomy_prefix",
                "pre_role_exclude",
                "pre_ignore_suffix",
                "source_rules_sha256",
                "content_sha256",
                "rules",
            }
        ),
    )
    if pack.get("schema") != NOT_PRESENTED_SCHEMA:
        raise NotPresentedError(f"not_presented.schema must equal {NOT_PRESENTED_SCHEMA}")
    content_sha256 = _verify_content_digest(pack, field="not_presented")
    pack_id = _identifier(pack.get("pack_id"), field="not_presented.pack_id")
    pack_version = _version(pack.get("pack_version"), field="not_presented.pack_version")
    available_at = _utc(pack.get("available_at"), field="not_presented.available_at")
    na_basis = _text(pack.get("na_basis"), field="not_presented.na_basis")
    if na_basis not in _ALLOWED_NA_BASIS:
        raise NotPresentedError(f"not_presented.na_basis must be one of {sorted(_ALLOWED_NA_BASIS)}")
    prefix = _text(pack.get("child_taxonomy_prefix"), field="not_presented.child_taxonomy_prefix")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", prefix):
        raise NotPresentedError("not_presented.child_taxonomy_prefix must be a bare taxonomy prefix")
    exclude, exclude_re = _regex(pack.get("pre_role_exclude"), field="not_presented.pre_role_exclude")
    ignore, ignore_re = _regex(pack.get("pre_ignore_suffix"), field="not_presented.pre_ignore_suffix")
    source_sha = _text(pack.get("source_rules_sha256"), field="not_presented.source_rules_sha256")
    if not _SHA256.fullmatch(source_sha):
        raise NotPresentedError("not_presented.source_rules_sha256 must be a lowercase SHA-256 digest")
    known = frozenset(known_metric_ids) if known_metric_ids is not None else None
    rules: dict[str, NotPresentedRule] = {}
    for index, item in enumerate(_require_list(pack.get("rules"), field="not_presented.rules")):
        rule = _rule_from_raw(item, field=f"not_presented.rules[{index}]", known_metric_ids=known)
        if rule.metric_id in rules:
            raise NotPresentedError(f"not_presented.rules repeats metric {rule.metric_id!r}")
        if rule.rule.available_at < available_at:
            raise NotPresentedError(
                f"not_presented.rules[{index}].rule.available_at precedes the pack's available_at"
            )
        rules[rule.metric_id] = rule
    if not rules:
        raise NotPresentedError("not_presented.rules must not be empty")
    return NotPresentedPack(
        pack_id=pack_id,
        pack_version=pack_version,
        available_at=available_at,
        na_basis=na_basis,
        child_taxonomy_prefix=prefix,
        pre_role_exclude=exclude,
        pre_ignore_suffix=ignore,
        source_rules_sha256=source_sha,
        content_sha256=content_sha256,
        rules=rules,
        pre_role_exclude_re=exclude_re,
        pre_ignore_suffix_re=ignore_re,
    )


def load_not_presented_pack(
    path: str | Path | None = None,
    *,
    known_metric_ids: Iterable[str] | None = None,
) -> NotPresentedPack:
    target = Path(path) if path is not None else DEFAULT_NOT_PRESENTED_PACK_PATH
    return not_presented_pack_from_dict(
        _load_yaml(target, label="not_presented"),
        known_metric_ids=known_metric_ids,
    )


# ---------------------------------------------------------------- parsing --


def parse_calculation_networks(content: bytes) -> CalculationNetworks:
    """Keep each calculationLink element separate (census semantics), arcs in order."""
    root = _parse_xml(content, name="calculation linkbase")
    links: list[tuple[str, Mapping[str, tuple[tuple[str, Decimal], ...]]]] = []
    for link in root.iter(f"{{{LINK}}}calculationLink"):
        role = _xlink(link, "role")
        if not role:
            raise StatementGraphError("calculation network is missing xlink:role")
        locs: dict[str, str] = {}
        for loc in link.findall(f"{{{LINK}}}loc"):
            label = _xlink(loc, "label")
            href = _xlink(loc, "href")
            if label and href:
                locs[label] = concept_from_href(href)
        by_parent: dict[str, list[tuple[str, Decimal]]] = {}
        for arc in link.findall(f"{{{LINK}}}calculationArc"):
            if arc.get("use") == "prohibited":
                continue
            frm = _xlink(arc, "from")
            to = _xlink(arc, "to")
            if frm not in locs or to not in locs:
                continue
            raw_weight = arc.get("weight") or "1"
            try:
                weight = Decimal(raw_weight)
            except InvalidOperation as exc:
                raise StatementGraphError("calculation arc weight is not a decimal") from exc
            if not weight.is_finite():
                raise StatementGraphError("calculation arc weight is not finite")
            by_parent.setdefault(locs[frm], []).append((locs[to], weight))
        links.append((role, {parent: tuple(children) for parent, children in by_parent.items()}))
    return CalculationNetworks(links=tuple(links))


def parse_presentation_networks(content: bytes) -> PresentationNetworks:
    root = _parse_xml(content, name="presentation linkbase")
    links: list[tuple[str, frozenset[str]]] = []
    for link in root.iter(f"{{{LINK}}}presentationLink"):
        role = _xlink(link, "role") or ""
        locals_: set[str] = set()
        for loc in link.findall(f"{{{LINK}}}loc"):
            href = _xlink(loc, "href")
            if href:
                local = _local_name(concept_from_href(href))
                if local:
                    locals_.add(local)
        links.append((role, frozenset(locals_)))
    return PresentationNetworks(links=tuple(links))


# ------------------------------------------------------------- evaluation --


def _round_int(value: Decimal) -> int:
    return int(value.to_integral_value(rounding=ROUND_HALF_EVEN))


def _off_units(values: Iterable[int]) -> int:
    involved = list(values)
    grain = 1
    for exponent in range(1, _MAX_OFF_UNITS_EXPONENT + 1):
        step = 10**exponent
        if all(value % step == 0 for value in involved):
            grain = step
        else:
            break
    return grain


def _empty_verdict(
    metric_id: str,
    reason: str,
    *,
    rules_sha256: str,
    rule: NotPresentedRule | None = None,
    cal_sha256: str | None = None,
    pre_sha256: str | None = None,
    accession: str | None = None,
) -> NotPresentedVerdict:
    return NotPresentedVerdict(
        metric_id=metric_id,
        outcome=OUTCOME_ABSENT,
        reason=reason,
        fails=(reason,),
        np_kind=None,
        na_basis=None,
        rule_id=rule.rule.rule_id if rule is not None else None,
        rule_version=rule.rule.version if rule is not None else None,
        rules_sha256=rules_sha256,
        parent_concepts=(),
        roles_checked=0,
        children_n=0,
        children_with_fact_n=0,
        footing=None,
        off_units=None,
        extension_children=(),
        cal_sha256=cal_sha256,
        pre_sha256=pre_sha256,
        accession=accession,
    )


def evaluate_not_presented(
    pack: NotPresentedPack,
    rule: NotPresentedRule,
    *,
    calculation: CalculationNetworks,
    presentation: PresentationNetworks,
    facts_in_context: Mapping[str, Decimal],
) -> NotPresentedVerdict:
    """Pure census-parity evaluation of one metric in one slot context.

    ``facts_in_context`` maps a prefixed concept to its single, unambiguous,
    visible, consolidated USD value in the slot's exact accession and period.
    The caller resolves duplicates fail-closed before calling.
    """
    for concept, value in facts_in_context.items():
        if not isinstance(value, Decimal) or not value.is_finite():
            raise NotPresentedError(f"fact {concept!r} must be a finite Decimal")
    calc_parents = calculation.parents()
    parents: list[str] = []
    for tier in rule.parent_tiers:
        candidates = [concept for concept in tier if concept in calc_parents and concept in facts_in_context]
        if candidates:
            parents = candidates
            break
    if not parents:
        return _empty_verdict(rule.metric_id, "np_no_parent", rules_sha256=pack.content_sha256, rule=rule)

    fails: set[str] = set()
    extension_children: set[str] = set()
    stats = {"roles": 0, "children": 0, "with_fact": 0, "comparisons": 0}
    off_units: list[int] = []
    child_prefix = f"{pack.child_taxonomy_prefix}:"

    def check_children_of(owner: str, owner_value: Decimal | None, seen: set[str]) -> None:
        for _index, kids in calculation.children_by_link(owner):
            stats["roles"] += 1
            kids_with: list[tuple[Decimal, Decimal]] = []
            for child, weight in kids:
                stats["children"] += 1
                child_local = _local_name(child)
                child_value = facts_in_context.get(child)
                if child_value is not None:
                    stats["with_fact"] += 1
                    kids_with.append((weight, child_value))
                if not child.startswith(child_prefix):
                    fails.add("np_extension_child")
                    extension_children.add(child)
                if rule.family_re.search(child_local):
                    fails.add("np_family_in_calc")
                if rule.containers_re is not None and rule.containers_re.search(child_local):
                    if child in seen:
                        continue
                    seen.add(child)
                    if child not in calc_parents:
                        fails.add("np_container_leaf")
                    else:
                        check_children_of(child, facts_in_context.get(child), seen)
            if owner_value is None:
                continue
            if not kids_with:
                fails.add("np_children_no_facts")
                continue
            total = sum(_round_int(weight * _round_int(value)) for weight, value in kids_with)
            parent_total = _round_int(owner_value)
            stats["comparisons"] += 1
            if total != parent_total:
                fails.add("np_unbalanced")
                if not off_units:
                    grain = _off_units([parent_total, *(_round_int(value) for _w, value in kids_with)])
                    off_units.append(abs(parent_total - total) // grain)

    for parent in parents:
        check_children_of(parent, facts_in_context[parent], {parent})

    for parent in parents:
        parent_local = _local_name(parent)
        for role, locals_ in presentation.links:
            if pack.pre_role_exclude_re.search(role) or parent_local not in locals_:
                continue
            if any(
                not pack.pre_ignore_suffix_re.search(local) and rule.family_re.search(local)
                for local in locals_
            ):
                fails.add("np_family_in_statement_pre")
                break

    if any(rule.family_re.search(_local_name(concept)) for concept in facts_in_context):
        fails.add("np_family_fact")

    ordered = tuple(reason for reason in REASON_ORDER if reason in fails)
    not_presented = not ordered
    if off_units:
        footing: str | None = FOOTING_OFF
    elif stats["comparisons"] > 0:
        footing = FOOTING_EXACT
    else:
        footing = None
    return NotPresentedVerdict(
        metric_id=rule.metric_id,
        outcome=OUTCOME_NOT_PRESENTED if not_presented else OUTCOME_ABSENT,
        reason=ordered[0] if ordered else None,
        fails=ordered,
        np_kind=rule.np_kind if not_presented else None,
        na_basis=pack.na_basis if not_presented else None,
        rule_id=rule.rule.rule_id,
        rule_version=rule.rule.version,
        rules_sha256=pack.content_sha256,
        parent_concepts=tuple(parents),
        roles_checked=stats["roles"],
        children_n=stats["children"],
        children_with_fact_n=stats["with_fact"],
        footing=footing,
        off_units=off_units[0] if off_units else None,
        extension_children=tuple(sorted(extension_children)),
    )


def evaluate_not_presented_package(
    pack: NotPresentedPack,
    metric_id: str,
    *,
    calculation: bytes | None,
    presentation: bytes | None,
    facts_in_context: Mapping[str, Decimal],
    recorded_at: datetime,
    accession: str,
) -> NotPresentedVerdict:
    """Evaluate from raw linkbase bytes; binds the verdict to their SHA-256s."""
    rules_sha = pack.content_sha256
    rule = pack.visible_rule(metric_id, recorded_at=recorded_at)
    if rule is None:
        return _empty_verdict(metric_id, "np_no_rule", rules_sha256=rules_sha, accession=accession)
    if not calculation:
        return _empty_verdict(metric_id, "np_no_calc_linkbase", rules_sha256=rules_sha, rule=rule, accession=accession)
    cal_sha = hashlib.sha256(calculation).hexdigest()
    if not presentation:
        return _empty_verdict(
            metric_id,
            "np_no_presentation_linkbase",
            rules_sha256=rules_sha,
            rule=rule,
            cal_sha256=cal_sha,
            accession=accession,
        )
    pre_sha = hashlib.sha256(presentation).hexdigest()
    try:
        calc_networks = parse_calculation_networks(calculation)
        pre_networks = parse_presentation_networks(presentation)
    except (StatementGraphError, ET.ParseError):
        return _empty_verdict(
            metric_id,
            "np_parse_error",
            rules_sha256=rules_sha,
            rule=rule,
            cal_sha256=cal_sha,
            pre_sha256=pre_sha,
            accession=accession,
        )
    verdict = evaluate_not_presented(
        pack,
        rule,
        calculation=calc_networks,
        presentation=pre_networks,
        facts_in_context=facts_in_context,
    )
    return NotPresentedVerdict(
        **{
            **verdict.__dict__,
            "cal_sha256": cal_sha,
            "pre_sha256": pre_sha,
            "accession": accession,
        }
    )


_EVIDENCE_KEYS = frozenset(
    {
        "np_kind",
        "np_rule_id",
        "np_rule_version",
        "np_rules_sha256",
        "np_parent_concepts",
        "np_roles_checked",
        "np_children_n",
        "np_children_with_fact_n",
        "np_footing",
        "np_cal_sha256",
        "np_pre_sha256",
        "np_accession",
    }
)
_MAX_EVIDENCE_PARENTS = 16


def _evidence_count(value: Any, *, field: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise NotPresentedError(f"{field} must be an integer >= {minimum}")
    return value


def _evidence_sha(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise NotPresentedError(f"{field} must be a lowercase SHA-256 hex digest")
    return value


def _evidence_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NotPresentedError(f"{field} must be non-empty trimmed text")
    return value


@dataclass(frozen=True)
class NotPresentedEvidence:
    """The receipt object a ``not_presented`` cell carries (no value field).

    It binds the verdict to its rule identity, the pack digest, and the exact
    linkbase bytes, so the engine can recompute it from the filing package.
    ``na_basis`` lives on the cell provenance itself, beside this object.
    """

    np_kind: str
    rule_id: str
    rule_version: str
    rules_sha256: str
    parent_concepts: tuple[str, ...]
    roles_checked: int
    children_n: int
    children_with_fact_n: int
    footing: str
    cal_sha256: str
    pre_sha256: str
    accession: str

    def __post_init__(self) -> None:
        if self.np_kind not in _ALLOWED_NP_KINDS:
            raise NotPresentedError("np_kind is not a governed not-presented kind")
        _evidence_text(self.rule_id, field="np_rule_id")
        if not self.rule_id.startswith("not_presented."):
            raise NotPresentedError("np_rule_id must name a not-presented rule")
        _evidence_text(self.rule_version, field="np_rule_version")
        _evidence_sha(self.rules_sha256, field="np_rules_sha256")
        parents = self.parent_concepts
        if (
            not isinstance(parents, tuple)
            or not parents
            or len(parents) > _MAX_EVIDENCE_PARENTS
            or len(set(parents)) != len(parents)
            or any(not isinstance(item, str) or not _QNAME.fullmatch(item) for item in parents)
        ):
            raise NotPresentedError("np_parent_concepts must be unique prefixed concepts")
        _evidence_count(self.roles_checked, field="np_roles_checked", minimum=1)
        _evidence_count(self.children_n, field="np_children_n", minimum=1)
        _evidence_count(self.children_with_fact_n, field="np_children_with_fact_n", minimum=1)
        if self.children_with_fact_n > self.children_n:
            raise NotPresentedError("np_children_with_fact_n cannot exceed np_children_n")
        if self.footing != FOOTING_EXACT:
            raise NotPresentedError("a not-presented verdict requires exact footing")
        _evidence_sha(self.cal_sha256, field="np_cal_sha256")
        _evidence_sha(self.pre_sha256, field="np_pre_sha256")
        _evidence_text(self.accession, field="np_accession")

    @classmethod
    def from_verdict(cls, verdict: NotPresentedVerdict) -> "NotPresentedEvidence":
        if not verdict.is_not_presented:
            raise NotPresentedError("only a not_presented verdict carries cell evidence")
        return cls(
            np_kind=verdict.np_kind or "",
            rule_id=verdict.rule_id or "",
            rule_version=verdict.rule_version or "",
            rules_sha256=verdict.rules_sha256,
            parent_concepts=verdict.parent_concepts,
            roles_checked=verdict.roles_checked,
            children_n=verdict.children_n,
            children_with_fact_n=verdict.children_with_fact_n,
            footing=verdict.footing or "",
            cal_sha256=verdict.cal_sha256 or "",
            pre_sha256=verdict.pre_sha256 or "",
            accession=verdict.accession or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "np_kind": self.np_kind,
            "np_rule_id": self.rule_id,
            "np_rule_version": self.rule_version,
            "np_rules_sha256": self.rules_sha256,
            "np_parent_concepts": list(self.parent_concepts),
            "np_roles_checked": self.roles_checked,
            "np_children_n": self.children_n,
            "np_children_with_fact_n": self.children_with_fact_n,
            "np_footing": self.footing,
            "np_cal_sha256": self.cal_sha256,
            "np_pre_sha256": self.pre_sha256,
            "np_accession": self.accession,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "NotPresentedEvidence":
        if not isinstance(value, Mapping) or set(value) != _EVIDENCE_KEYS:
            raise NotPresentedError("not_presented evidence must carry exactly the np_* keys")
        parents = value["np_parent_concepts"]
        if not isinstance(parents, (list, tuple)):
            raise NotPresentedError("np_parent_concepts must be a list")
        return cls(
            np_kind=value["np_kind"],
            rule_id=value["np_rule_id"],
            rule_version=value["np_rule_version"],
            rules_sha256=value["np_rules_sha256"],
            parent_concepts=tuple(parents),
            roles_checked=value["np_roles_checked"],
            children_n=value["np_children_n"],
            children_with_fact_n=value["np_children_with_fact_n"],
            footing=value["np_footing"],
            cal_sha256=value["np_cal_sha256"],
            pre_sha256=value["np_pre_sha256"],
            accession=value["np_accession"],
        )


def package_linkbases(package: Any) -> tuple[bytes | None, bytes | None]:
    """Return the stored calculation and presentation bytes of one package.

    Duck-typed over ``manifest``/``members`` (admitted and golden packages).
    A role with zero or several stored members yields ``None`` so the caller
    stays absent; nothing is guessed.
    """
    manifest = getattr(package, "manifest", None)
    members = getattr(package, "members", None)
    if not isinstance(manifest, Mapping) or not isinstance(members, Mapping):
        return None, None
    listed = manifest.get("members")
    if not isinstance(listed, (list, tuple)):
        return None, None
    found: dict[str, list[bytes]] = {"calculation": [], "presentation": []}
    for item in listed:
        if not isinstance(item, Mapping) or item.get("state") != "stored":
            continue
        role = item.get("role")
        if role not in found:
            continue
        content = members.get(item.get("name"))
        if isinstance(content, (bytes, bytearray)) and content:
            found[role].append(bytes(content))
        else:
            found[role].append(b"")
    cal = found["calculation"][0] if len(found["calculation"]) == 1 else None
    pre = found["presentation"][0] if len(found["presentation"]) == 1 else None
    return cal or None, pre or None


def verify_not_presented_evidence(
    pack: NotPresentedPack,
    metric_id: str,
    evidence: Mapping[str, Any],
    *,
    calculation: bytes | None,
    presentation: bytes | None,
    facts_in_context: Mapping[str, Decimal],
    recorded_at: datetime,
) -> None:
    """Recompute the verdict from package bytes and refuse any evidence drift."""
    accession = evidence.get("np_accession")
    if not isinstance(accession, str) or not accession:
        raise NotPresentedError("not_presented evidence is missing np_accession")
    verdict = evaluate_not_presented_package(
        pack,
        metric_id,
        calculation=calculation,
        presentation=presentation,
        facts_in_context=facts_in_context,
        recorded_at=recorded_at,
        accession=accession,
    )
    if not verdict.is_not_presented:
        raise NotPresentedError(f"not_presented evidence does not recompute: {verdict.reason}")
    if dict(evidence) != verdict.evidence():
        raise NotPresentedError("not_presented evidence does not match its recomputation")


__all__ = [
    "CORE_NOT_PRESENTED_PACK_ID",
    "CalculationNetworks",
    "DEFAULT_NOT_PRESENTED_PACK_PATH",
    "FOOTING_EXACT",
    "FOOTING_OFF",
    "NA_BASIS_NOT_PRESENTED_ITEM",
    "NOT_PRESENTED_REASON",
    "NOT_PRESENTED_SCHEMA",
    "NP_KIND_ITEM",
    "NotPresentedError",
    "NotPresentedEvidence",
    "NotPresentedPack",
    "NotPresentedRule",
    "NotPresentedVerdict",
    "PresentationNetworks",
    "REASON_ORDER",
    "evaluate_not_presented",
    "evaluate_not_presented_package",
    "load_not_presented_pack",
    "not_presented_pack_from_dict",
    "package_linkbases",
    "parse_calculation_networks",
    "parse_presentation_networks",
    "verify_not_presented_evidence",
]
