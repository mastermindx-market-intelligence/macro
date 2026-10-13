"""Dataset contracts + the static lineage DAG (Data OS §D5, §D9).

WHY THIS FILE EXISTS.  The house already owns the right contract primitive:
``collectors/base.py::ColumnContract``, born from china_connect/northbound hiding the
death of ``net``/``buy``/``sell`` for ~2 years behind a still-live ``turnover``
column — frame-grain freshness could not see it, so the contract moved down to the
COLUMN.  That primitive is per-adapter and per-column.  What is missing is the tier
above it: nothing anywhere declares what a DATASET is, who produces it, which clocks
it carries, which basis its price columns are on, or what reads it.  So every new
session re-derives all of that by grepping, and every consumer's assumption lives
only in the consumer.

This module is that tier, and it deliberately introduces NO new store (§D9).
Lineage is three pieces, two of which already exist:

1. every dataset has a stable ``dataset_id`` declaring ``inputs: [dataset_id]``,
   giving a static dependency DAG with no runtime instrumentation
   (:meth:`Registry.dag`);
2. every produced artifact writes a receipt — already the house idiom
   (``contracts/*_receipt.schema.json``);
3. a lineage query is "walk the DAG, read the receipts".

STATUS IS PART OF THE CONTRACT.  A registry that lists a dataset which does not exist
is worse than no registry: the next session builds against it.  Anything not yet
produced is ``status: PROPOSED`` and says so in its own row.

:func:`validate_registry` RETURNS violations and neither prints nor exits.  Severity
is the caller's decision — a test may fail on any violation while a catalog builder
may want to render them — and a validator that calls ``sys.exit`` cannot be used by
either.

STDLIB ONLY AT IMPORT TIME.  ``yaml`` is imported inside :func:`load_registry`, so a
lane that only needs the vocabulary (the enums, :class:`DatasetContract`) pays
nothing for a dependency it will not use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any, Mapping

from lib.dataos import price
from lib.dataos.temporal import TemporalProfile

__all__ = [
    "RegistryError",
    "Layer",
    "DatasetStatus",
    "ConflictPolicy",
    "DatasetContract",
    "Registry",
    "REGISTRY_PATH",
    "BASIS_VALUES",
    "RIGHTS_KEYS",
    "RIGHTS_VALUES",
    "CLOCK_VALUES",
    "EVIDENCE_ROOTS",
    "load_registry",
    "validate_registry",
    "ActionInputStatus",
    "ActionInputVerdict",
    "qualify_action_input",
    "ACTION_INPUT_FIELDS",
    "ACTION_INPUT_OPTIONAL_FIELDS",
    "ACTION_INPUT_ORIGINS",
    "ACTION_INPUT_RESPONSES",
    "ACTION_FIELD_CONVENTIONS",
    "ACTION_CONVENTIONS_ADMISSIBLE",
    "ACTION_CONVENTIONS_NEVER_ADMISSIBLE",
]

#: Resolved against THIS FILE, never the cwd — the nightly, the CI packs and a
#: developer shell all run from different directories, and a cwd-relative default is
#: a config file that silently is not there.
REGISTRY_PATH: Path = Path(__file__).resolve().parents[2] / "config" / "dataset_registry.yml"


class RegistryError(ValueError):
    """The registry file itself is unreadable or structurally wrong."""


class Layer(Enum):
    """The five layers of §D1.  ``L2`` is where the price-basis law lives.

    Law: **derived data must never masquerade as source.**  In-repo precedent that
    this is a real, expensive failure — ``DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT``
    stop-shipped an entire CN limit-alpha program because a vendor-*adjusted* price
    was used where the exchange's *raw print* was the only lawful input.
    """

    L0_SOURCE = "L0"
    L1_NORMALIZED = "L1"
    L2_CANONICAL = "L2"
    L3_DERIVED = "L3"
    L4_INTELLIGENCE = "L4"


class DatasetStatus(Enum):
    """Does this dataset EXIST?  A registry that lies about this is a trap."""

    PRODUCED = "PRODUCED"      # the store exists and a producer writes it today
    PROPOSED = "PROPOSED"      # declared here, not yet produced by anything
    RETIRED = "RETIRED"        # was produced; kept so its consumers stay explainable


class ConflictPolicy(Enum):
    """Multi-vendor conflict resolution (§D7).

    ``DISCREPANT_MAJOR`` on a canonical field quarantines the value, serves last-good
    and opens an incident — it never silently picks whichever API answered last.
    """

    PRIMARY_ONLY = "PRIMARY_ONLY"
    FALLBACK = "FALLBACK"
    DOMAIN_AUTHORITY = "DOMAIN_AUTHORITY"
    CROSS_VALIDATE = "CROSS_VALIDATE"
    COMPOSITE = "COMPOSITE"


#: Fields that must be non-empty on every contract.  Deliberately short: a required
#: field nobody can fill honestly gets filled dishonestly.
REQUIRED_FIELDS: tuple[str, ...] = (
    "dataset_id", "layer", "owner", "producer", "storage", "format",
    "grain", "temporal_profile", "version", "status",
)

# ── R00 consumer declarations (2026-10-13, D00.D6) ────────────────────────────
# Five OPTIONAL fields so the registry — not a directory name or a licensing
# label — answers "what is this data, on which basis/population/clocks, and may
# I compute/redistribute it" for the three frozen consumers.  Validated ONLY
# when present: an absent field is "not declared", never "false", and never a
# guess (a row that cannot honestly measure e.g. its venues simply omits the
# block and carries the gap in `notes`).

#: Row-level price basis.  `raw`/`sadj`/`tradj` are :class:`price.AdjustmentBasis`
#: values; `not_applicable` marks a row no schema column of which carries a basis
#: (membership, reference and receipt stores).  Must AGREE with every schema
#: column that carries its own `basis:` — one row label may never claim less
#: adjustment than a constituent column (D00.D3).
BASIS_VALUES: tuple[str, ...] = (
    price.AdjustmentBasis.RAW.value,
    price.AdjustmentBasis.SADJ.value,
    price.AdjustmentBasis.TRADJ.value,
    "not_applicable",
)

#: The three INDEPENDENT rights (K01.02 / D00 "Rights"): purchase != computation
#: != redistribution, and no one of them is ever inferred from another.
RIGHTS_KEYS: tuple[str, ...] = ("purchase_access", "internal_computation", "redistribution")
#: `granted` requires an evidence pointer; `unverified` is the honest default for
#: every right nobody has evidenced; `not_granted` is an affirmative denial.
RIGHTS_VALUES: tuple[str, ...] = ("granted", "not_granted", "unverified")

#: Row-level clocks (D00.D1): the two observable clocks plus the DERIVED marker —
#: a DERIVED profile has no clock of its own, so the row says so instead of
#: inventing one.
CLOCK_VALUES: tuple[str, ...] = ("published_at", "ingested_at", "derived")

#: Where a `granted` right's evidence may point: a decision key (`DEC:<KEY>` /
#: `DSC:<KEY>`) or a repo path under these roots (optional `#anchor`).  A path
#: under `data/`, a bare directory, a URL or the row's own `licensing:` label is
#: NOT evidence (R00.02) — a readable directory and a subscription label grant
#: nothing.
EVIDENCE_ROOTS: tuple[str, ...] = ("docs/", "research/", "agentos/")


@dataclass(frozen=True)
class DatasetContract:
    """What one dataset owes its consumers (§D5).

    ``layer``/``status``/``conflict_policy``/``temporal_profile`` hold the coerced
    enum when the YAML value is recognised and the RAW STRING when it is not — so an
    unknown ``temporal_profile`` reaches :func:`validate_registry` as a reportable
    violation instead of exploding at load time and taking the whole catalog with it.
    """

    dataset_id: str
    layer: Layer | str
    owner: str
    producer: str
    storage: str
    format: str
    grain: tuple[str, ...]
    temporal_profile: TemporalProfile | str
    version: str
    status: DatasetStatus | str
    id_column: str = ""
    id_type: str = ""
    schema: dict[str, dict[str, Any]] = field(default_factory=dict)
    timezone: str = ""
    frequency: str = ""
    adjustment: str = ""
    vendor: str = ""
    endpoint: str = ""
    conflict_policy: ConflictPolicy | str = ConflictPolicy.PRIMARY_ONLY
    freshness_sla_hours: float | None = None
    quality_checks: tuple[str, ...] = ()
    #: Functions/modules that READ this store, as code paths — prose, for a human
    #: chasing a change's blast radius.  Deliberately NOT named ``consumers``: that
    #: word already means the reverse edge of the lineage graph
    #: (:meth:`Registry.consumers_of`, which answers in dataset_ids), and one name for
    #: two different answers is how a lineage query stops being trustworthy.
    code_consumers: tuple[str, ...] = ()
    #: dataset_ids ONLY.  This IS the DAG; a code path here is not an edge.
    inputs: tuple[str, ...] = ()
    licensing: str = ""
    supersedes: str = ""
    notes: str = ""
    #: ── R00 consumer declarations, all optional (see BASIS_VALUES et al.) ──
    #: Row-level price basis; "" = not declared.  Kept as the raw string when the
    #: value is unrecognised so :func:`validate_registry` can report it.
    basis: str = ""
    #: ``{market, venues, universe}``; empty dict = not declared (R00: a row that
    #: cannot honestly measure one of the keys omits the whole block).
    population: dict[str, Any] = field(default_factory=dict)
    #: Declared clocks; None = not declared, () = declared empty (a violation).
    clocks: tuple[str, ...] | None = None
    #: The three rights (+ optional ``evidence`` mapping); empty dict = not declared.
    rights: dict[str, Any] = field(default_factory=dict)
    #: Corporate-action point-in-time binding; None = not declared, never False.
    point_in_time_corporate_actions: bool | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "DatasetContract":
        """Build from one YAML mapping, coercing enums LENIENTLY (see class docstring)."""
        if not isinstance(data, dict):
            raise RegistryError(f"dataset entry must be a mapping, got {type(data).__name__}")
        identity = data.get("identity") or {}
        if not isinstance(identity, dict):
            raise RegistryError(
                f"{data.get('dataset_id')!r}: identity: must be a mapping of "
                "id_column/id_type"
            )
        schema = data.get("schema") or {}
        if not isinstance(schema, dict):
            raise RegistryError(f"{data.get('dataset_id')!r}: schema: must be a mapping")
        population = data.get("population") or {}
        if not isinstance(population, dict):
            raise RegistryError(
                f"{data.get('dataset_id')!r}: population: must be a mapping of "
                "market/venues/universe"
            )
        rights = data.get("rights") or {}
        if not isinstance(rights, dict):
            raise RegistryError(
                f"{data.get('dataset_id')!r}: rights: must be a mapping of "
                "purchase_access/internal_computation/redistribution"
            )
        pit = data.get("point_in_time_corporate_actions")
        if pit is not None and not isinstance(pit, bool):
            # RegistryError, not a silent coercion: bool("false") is True, so
            # truthiness here would INVERT the author's meaning.
            raise RegistryError(
                f"{data.get('dataset_id')!r}: point_in_time_corporate_actions: must be "
                f"a bool, got {type(pit).__name__} {pit!r}"
            )
        clocks = data.get("clocks")
        sla = data.get("freshness_sla_hours")
        return cls(
            dataset_id=str(data.get("dataset_id") or ""),
            layer=_coerce(Layer, data.get("layer")),
            owner=str(data.get("owner") or ""),
            producer=str(data.get("producer") or ""),
            storage=str(data.get("storage") or ""),
            format=str(data.get("format") or ""),
            grain=_as_tuple(data.get("grain")),
            temporal_profile=_coerce(TemporalProfile, data.get("temporal_profile")),
            version=str(data.get("version") or ""),
            status=_coerce(DatasetStatus, data.get("status")),
            id_column=str(identity.get("id_column") or ""),
            id_type=str(identity.get("id_type") or ""),
            schema={str(k): dict(v or {}) for k, v in schema.items()},
            timezone=str(data.get("timezone") or ""),
            frequency=str(data.get("frequency") or ""),
            adjustment=str(data.get("adjustment") or ""),
            vendor=str(data.get("vendor") or ""),
            endpoint=str(data.get("endpoint") or ""),
            # A dataset that names no policy has exactly one vendor, which IS
            # PRIMARY_ONLY — defaulting it here keeps a single-vendor row from
            # having to recite a decision nobody made.
            conflict_policy=_coerce(
                ConflictPolicy,
                data.get("conflict_policy") or ConflictPolicy.PRIMARY_ONLY.value,
            ),
            freshness_sla_hours=float(sla) if sla is not None else None,
            quality_checks=_as_tuple(data.get("quality_checks")),
            code_consumers=_as_tuple(data.get("code_consumers")),
            inputs=_as_tuple(data.get("inputs")),
            licensing=str(data.get("licensing") or ""),
            supersedes=str(data.get("supersedes") or ""),
            notes=str(data.get("notes") or ""),
            basis=str(data.get("basis") or ""),
            population=dict(population),
            clocks=None if clocks is None else _as_tuple(clocks),
            rights=dict(rights),
            point_in_time_corporate_actions=pit,
        )


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def _coerce(enum_cls, value):
    """Enum member when the value is recognised, else the raw string (or ``""``)."""
    if value is None:
        return ""
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(str(value).strip())
    except ValueError:
        return str(value)


def _is_evidence_pointer(pointer: object) -> bool:
    """Is *pointer* a lawful evidence form for a ``granted`` right (R00.02)?

    Lawful: ``DEC:<KEY>`` / ``DSC:<KEY>`` with a non-empty key, or a path under
    :data:`EVIDENCE_ROOTS` with a non-empty remainder and an optional ``#anchor``.
    NOT evidence: a URL, a path under ``data/``, a bare directory (trailing ``/``
    or nothing after the root), or any free prose such as the row's own
    ``licensing:`` label — none of those is a decision, and a licensing label
    asserting its own grant is the exact self-reference R00.02 exists to refuse.
    """
    if not isinstance(pointer, str):
        return False
    text = pointer.strip()
    if not text or "://" in text or text.lower().startswith("www."):
        return False
    body = text.split("#", 1)[0].strip()
    if not body:
        return False
    if body.startswith(("DEC:", "DSC:")):
        return len(body) > 4 and not body.endswith(":")
    return (
        any(body.startswith(root) for root in EVIDENCE_ROOTS)
        and not body.endswith("/")
        and all(len(part) > 0 for part in body.split("/"))
    )


class Registry:
    """An ordered collection of :class:`DatasetContract`, indexed by ``dataset_id``.

    The ORDERED tuple is retained rather than only the index, because a duplicate
    ``dataset_id`` disappears into a dict and duplicate detection is one of the
    violations :func:`validate_registry` owes the caller.
    """

    __slots__ = ("_contracts", "_by_id")

    def __init__(self, contracts) -> None:
        self._contracts: tuple[DatasetContract, ...] = tuple(contracts)
        self._by_id: dict[str, DatasetContract] = {c.dataset_id: c for c in self._contracts}

    def __len__(self) -> int:
        return len(self._contracts)

    def __iter__(self):
        return iter(self._contracts)

    def all(self) -> tuple[DatasetContract, ...]:
        """Every contract, in file order."""
        return self._contracts

    def get(self, dataset_id: str) -> DatasetContract | None:
        """One contract by id, or ``None``.  Last wins on a duplicate id."""
        return self._by_id.get(dataset_id)

    def ids(self) -> tuple[str, ...]:
        return tuple(c.dataset_id for c in self._contracts)

    def duplicate_ids(self) -> tuple[str, ...]:
        seen: set[str] = set()
        dupes: list[str] = []
        for c in self._contracts:
            if c.dataset_id in seen and c.dataset_id not in dupes:
                dupes.append(c.dataset_id)
            seen.add(c.dataset_id)
        return tuple(dupes)

    def inputs_of(self, dataset_id: str) -> tuple[str, ...]:
        """The dataset_ids this dataset reads (declared, not observed)."""
        contract = self.get(dataset_id)
        return contract.inputs if contract else ()

    def consumers_of(self, dataset_id: str) -> tuple[str, ...]:
        """The dataset_ids that declare this one as an input — the reverse edge.

        Derived from ``inputs`` rather than from each contract's ``code_consumers``
        prose field on purpose: the reverse edge must be a FACT of the graph, and a
        hand-maintained consumer list is exactly the thing that rots first.  The two
        answer different questions — dataset_ids here, code paths there — and they are
        kept under different names because they were once both called "consumers" and
        a caller could not tell which one it was holding.
        """
        return tuple(c.dataset_id for c in self._contracts if dataset_id in c.inputs)

    def dag(self) -> tuple[tuple[str, str], ...]:
        """Dependency edges as ``(input_id, dataset_id)`` — flows in the data direction."""
        return tuple(
            (src, c.dataset_id) for c in self._contracts for src in c.inputs
        )


def load_registry(path: str | Path | None = None) -> Registry:
    """Read ``config/dataset_registry.yml`` (or *path*) into a :class:`Registry`."""
    import yaml  # lazy: keeps the vocabulary importable in a lane without pyyaml

    target = Path(path) if path is not None else REGISTRY_PATH
    if not target.exists():
        raise RegistryError(f"dataset registry not found at {target}")
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise RegistryError(f"{target}: top level must be a mapping, got {type(payload).__name__}")
    datasets = payload.get("datasets")
    if datasets is None:
        raise RegistryError(f"{target}: no `datasets:` key")
    if not isinstance(datasets, list):
        raise RegistryError(f"{target}: `datasets:` must be a list, got {type(datasets).__name__}")
    return Registry(DatasetContract.from_mapping(entry) for entry in datasets)


def validate_registry(registry: Registry) -> list[str]:
    """Human-readable violations, most structural first.  Returns; never prints or exits.

    Detects: duplicate ``dataset_id``; missing required field; unknown ``inputs``
    reference; ``temporal_profile`` outside the closed vocabulary; an ambiguous price
    column name on an L2/CANONICAL dataset (§D4's naming law, which binds at the
    canonical layer); and a cycle in the dependency DAG.

    R00 additions, validated ONLY when the field is present (absent = not
    declared, never "false"): ``basis`` outside :data:`BASIS_VALUES` or in
    disagreement with a schema column that carries its own ``basis:``;
    ``population`` without exactly the ``market``/``venues``/``universe`` keys;
    ``clocks`` empty or outside :data:`CLOCK_VALUES`; ``rights`` with an unknown
    or missing key, a value outside :data:`RIGHTS_VALUES`, or a ``granted`` right
    whose evidence pointer is missing or not a lawful :data:`EVIDENCE_ROOTS`
    form (R00.02 — rights never imply each other, K01.02).
    """
    violations: list[str] = []
    known_ids = set(registry.ids())

    for dupe in registry.duplicate_ids():
        violations.append(f"duplicate dataset_id: {dupe!r} appears more than once")

    for contract in registry.all():
        label = contract.dataset_id or "<unnamed dataset>"
        for name in REQUIRED_FIELDS:
            value = getattr(contract, name, None)
            if value in (None, "", ()):
                violations.append(f"{label}: missing required field {name!r}")
        if not isinstance(contract.temporal_profile, TemporalProfile):
            violations.append(
                f"{label}: temporal_profile {contract.temporal_profile!r} is not one of "
                f"({', '.join(p.value for p in TemporalProfile)})"
            )
        if not isinstance(contract.layer, Layer):
            violations.append(
                f"{label}: layer {contract.layer!r} is not one of "
                f"({', '.join(lay.value for lay in Layer)})"
            )
        if not isinstance(contract.status, DatasetStatus):
            violations.append(
                f"{label}: status {contract.status!r} is not one of "
                f"({', '.join(s.value for s in DatasetStatus)})"
            )
        if not isinstance(contract.conflict_policy, ConflictPolicy):
            violations.append(
                f"{label}: conflict_policy {contract.conflict_policy!r} is not one of "
                f"({', '.join(c.value for c in ConflictPolicy)})"
            )
        for src in contract.inputs:
            if src not in known_ids:
                violations.append(
                    f"{label}: declares input {src!r}, which is not a dataset_id in this registry"
                )
        if contract.layer is Layer.L2_CANONICAL:
            for column in contract.schema:
                if price.is_ambiguous(column):
                    violations.append(
                        f"{label}: column {column!r} is an ambiguous price name on an "
                        "L2/CANONICAL dataset — §D4 requires {field}_{basis} "
                        f"(e.g. {price.canonical_column('close', 'tradj')})"
                    )
        violations.extend(_consumer_field_violations(contract, label))

    violations.extend(_cycles(registry))
    return violations


def _consumer_field_violations(contract: DatasetContract, label: str) -> list[str]:
    """The R00 additive fields, each validated only when declared.

    Mirrors the module's report-not-raise contract: a bad VALUE reaches the
    caller as a readable violation, exactly like an unknown ``temporal_profile``,
    so one wrong row never takes the catalog down.  Structural impossibilities
    (``rights``/``population`` not a mapping, a non-bool
    ``point_in_time_corporate_actions``) are refused at load by
    :meth:`DatasetContract.from_mapping` because no honest contract can hold them.
    """
    out: list[str] = []

    if contract.basis:
        if contract.basis not in BASIS_VALUES:
            out.append(
                f"{label}: basis {contract.basis!r} is not one of "
                f"({', '.join(BASIS_VALUES)})"
            )
        else:
            column_bases = {
                column: spec.get("basis")
                for column, spec in contract.schema.items()
                if isinstance(spec, dict) and spec.get("basis")
            }
            if contract.basis == "not_applicable":
                if column_bases:
                    out.append(
                        f"{label}: basis 'not_applicable' but schema column(s) "
                        f"{sorted(column_bases)} carry a basis"
                    )
            else:
                for column, column_basis in sorted(column_bases.items()):
                    if column_basis != contract.basis:
                        out.append(
                            f"{label}: basis {contract.basis!r} disagrees with schema "
                            f"column {column!r} basis {column_basis!r}"
                        )

    if contract.population:
        keys = set(contract.population)
        if keys != {"market", "venues", "universe"}:
            out.append(
                f"{label}: population keys must be exactly "
                "('market', 'venues', 'universe'), got {sorted(keys)}"
            )
        else:
            for key in ("market", "universe"):
                value = contract.population.get(key)
                if not isinstance(value, str) or not value.strip():
                    out.append(f"{label}: population.{key} must be a non-empty string")
            venues = contract.population.get("venues")
            if not isinstance(venues, (list, tuple)) or not venues:
                out.append(f"{label}: population.venues must be a non-empty list of MICs")
            else:
                for venue in venues:
                    if not isinstance(venue, str) or not (
                        len(venue) == 4 and venue.isalnum() and venue.isupper()
                    ):
                        out.append(
                            f"{label}: population.venues entry {venue!r} is not a "
                            "4-letter uppercase MIC"
                        )

    if contract.clocks is not None:
        if not contract.clocks:
            out.append(f"{label}: clocks must be a non-empty list")
        for clock in contract.clocks:
            if clock not in CLOCK_VALUES:
                out.append(
                    f"{label}: clocks entry {clock!r} is not one of "
                    f"({', '.join(CLOCK_VALUES)})"
                )

    if contract.rights:
        keys = set(contract.rights)
        unknown = keys - set(RIGHTS_KEYS) - {"evidence"}
        missing = set(RIGHTS_KEYS) - keys
        if unknown:
            out.append(
                f"{label}: rights has unknown key(s) {sorted(unknown)}; only "
                f"{'/'.join(RIGHTS_KEYS)} (+ evidence) are allowed"
            )
        if missing:
            out.append(f"{label}: rights is missing key(s) {sorted(missing)}")
        evidence = contract.rights.get("evidence")
        if "evidence" in keys and not isinstance(evidence, dict):
            out.append(f"{label}: rights.evidence must be a mapping right -> pointer")
        for key in RIGHTS_KEYS:
            if key not in keys:
                continue
            value = contract.rights[key]
            if value not in RIGHTS_VALUES:
                out.append(
                    f"{label}: rights.{key} {value!r} is not one of "
                    f"({', '.join(RIGHTS_VALUES)})"
                )
            elif value == "granted":
                pointer = (
                    evidence.get(key) if isinstance(evidence, dict) else None
                )
                if pointer is None:
                    out.append(
                        f"{label}: rights.{key} is granted without evidence (R00.02)"
                    )
                elif not _is_evidence_pointer(pointer):
                    out.append(
                        f"{label}: rights.{key} evidence {pointer!r} is not a DEC:/DSC: "
                        f"key or a path under {'/'.join(EVIDENCE_ROOTS)} (R00.02)"
                    )

    return out


def _cycles(registry: Registry) -> list[str]:
    """Every dependency cycle, reported once per cycle as a readable path."""
    edges: dict[str, tuple[str, ...]] = {
        c.dataset_id: tuple(s for s in c.inputs if registry.get(s) is not None)
        for c in registry.all()
    }
    found: list[str] = []
    seen_cycles: set[frozenset[str]] = set()
    state: dict[str, int] = {}   # 0 = visiting, 1 = done

    def walk(node: str, path: list[str]) -> None:
        state[node] = 0
        path.append(node)
        for src in edges.get(node, ()):
            if state.get(src) == 0:
                cycle = path[path.index(src):] + [src]
                key = frozenset(cycle)
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    found.append("cycle in dependency DAG: " + " -> ".join(cycle))
            elif src not in state:
                walk(src, path)
        path.pop()
        state[node] = 1

    for dataset_id in edges:
        if dataset_id not in state:
            walk(dataset_id, [])
    return found


# ── P01 action-input qualification (2026-10-13, D00.D3; P01.01–P01.04) ────────
# A corporate-action observation may enter a split/dividend factor only when it
# IS a confirmed, as-observed event with its own original receipt (D00.D3: "the
# only admitted source of events is a qualified original observation with its
# own receipt").  Everything a consumer used to reach for instead — a provider
# name, an `adjusted=true` flag, a price jump, a cumulative vendor factor, a
# current-share cash amount, an adjusted close series — is one of the refusals
# below, each with its own stable reason code, so P02–P04 never have to re-
# argue the distinction per call site.  Pure stdlib, no I/O: the caller brings
# the observation dict and (optionally) an already-loaded :class:`Registry`.

#: The keys an action observation MUST carry.  Absence is a caller bug
#: (``ValueError``), not a missing-data status — an observation that cannot say
#: where it came from has no verdict, and a silent ``None`` default would let
#: exactly the label-only inputs this function exists to refuse slip through a
#: forgotten key.
ACTION_INPUT_FIELDS: tuple[str, ...] = (
    "dataset_id", "endpoint", "field_convention", "receipt",
    "origin", "response", "rights_limited",
)

#: Keys the caller MAY carry; all other keys are refused, never ignored — an
#: ignored key is how `adjusted=true` hides next to a qualifying-looking dict.
ACTION_INPUT_OPTIONAL_FIELDS: tuple[str, ...] = ("provider", "adjusted_flag")

#: Where the observation claims to come from.  ``price_discontinuity`` is an
#: inference from the price path, never an event observation (D00.D3, P01.02).
ACTION_INPUT_ORIGINS: tuple[str, ...] = ("source_record", "price_discontinuity")

#: What the qualified source response held.  ``None`` = no response was
#: obtained (distinct from a qualified, authoritative empty).
ACTION_INPUT_RESPONSES: tuple[str, ...] = ("events", "empty")

#: Field conventions that state the event as observed: the exact split ratio
#: (``2:1`` → ``Fraction(2,1)``, D00.D3 SADJ) or the per-share cash amount as
#: declared by the payer (D00.D3/P04.02: original cash is one distinct fact).
ACTION_CONVENTIONS_ADMISSIBLE: tuple[str, ...] = (
    "as_observed_split_ratio", "as_declared_cash_amount",
)

#: Conventions that describe a DERIVED quantity and can never be an event:
#: a cumulative vendor adjustment factor, a cash amount restated on the
#: current share count, or an adjusted price series.  Each is real data —
#: just not an as-observed corporate event (P01.04, D00.D3 P04.02).
ACTION_CONVENTIONS_NEVER_ADMISSIBLE: tuple[str, ...] = (
    "cumulative_adjustment_factor", "current_share_adjusted_cash",
    "adjusted_close_only",
)

#: The closed convention vocabulary.  A convention outside it is a caller bug
#: (``ValueError``), not a verdict — inventing a fourth convention is how the
#: closed set stops being closed.
ACTION_FIELD_CONVENTIONS: tuple[str, ...] = (
    ACTION_CONVENTIONS_ADMISSIBLE + ACTION_CONVENTIONS_NEVER_ADMISSIBLE
)

#: Convention → refusal reason (rule 5).  One code per convention so a refusal
#: audit can name WHICH derived quantity was offered as an event.
_CONVENTION_REFUSALS: dict[str, str] = {
    "cumulative_adjustment_factor": "CUMULATIVE_FACTOR_NOT_AS_OBSERVED",
    "current_share_adjusted_cash": "CURRENT_SHARE_CASH_NOT_AS_DECLARED",
    "adjusted_close_only": "ADJUSTED_SERIES_NOT_AN_EVENT",
}


class ActionInputStatus(StrEnum):
    """May this observation enter a split/dividend factor?  Five answers.

    ``StrEnum`` (the :mod:`lib.dataos.price` idiom) so a verdict serialises
    without a ``.value`` dance and the statuses sort readably in a refusal log.
    """

    #: A qualified original observation with its own receipt, as-observed
    #: convention, from a produced source (D00.D3).  The ONLY status a factor
    #: may consume.
    CONFIRMED = "CONFIRMED"
    #: Inferred from a price discontinuity (P01.02).  Never confirmed, even
    #: when a receipt is attached: the receipt authenticates the *inference*,
    #: not an event observation.
    SUSPECTED = "SUSPECTED"
    #: Real data was offered as an event but is a derived quantity, a bare
    #: provider label, an unregistered/not-produced source, or names no
    #: convention at all.  Repairable only by bringing the real observation.
    UNQUALIFIED = "UNQUALIFIED"
    #: The qualified source answered and authoritatively held no action.
    #: A CONFIRMED answer to a different question — absence, not defect.
    NO_ACTION_IN_QUALIFIED_RESPONSE = "NO_ACTION_IN_QUALIFIED_RESPONSE"
    #: The event was never captured: no receipt, no response, or the capture
    #: is rights-limited (an unsupported family such as a rights issue —
    #: D00.D3 ``UNSUPPORTED_ACTION`` families are never coerced).
    UNCAPTURED = "UNCAPTURED"


@dataclass(frozen=True)
class ActionInputVerdict:
    """The outcome of :func:`qualify_action_input` — immutable and loggable.

    ``reason`` is a stable UPPER_SNAKE code (one per decision rule), so a
    consumer's refusal path can branch on it without parsing prose.  ``receipt``
    echoes the observation's receipt id/digest (or ``None``) so the verdict is
    self-identifying in a coverage report without re-reading the observation.
    """

    status: ActionInputStatus
    reason: str
    dataset_id: str
    receipt: str | None


def qualify_action_input(
    observation: Mapping[str, Any], *, registry: Registry | None = None
) -> ActionInputVerdict:
    """May this corporate-action observation enter a split/dividend factor?

    One pure function for P02–P04: given one observation mapping, return the
    :class:`ActionInputVerdict` for the FIRST matching decision rule below.
    Raises (never returns a verdict) when the observation is structurally not
    an action observation at all — an unknown key, a missing required key, a
    value outside a closed vocabulary, a non-bool flag — because a structurally
    impossible input has no honest status.

    Decision order (first match wins; D00.D3, P01.01–P01.04):

    1. ``origin == price_discontinuity`` → SUSPECTED / ``DISCONTINUITY_INFERRED``
       — even with a receipt (P01.02).
    2. ``rights_limited`` → UNCAPTURED / ``RIGHTS_LIMITED`` (P01.03).
    3. no receipt: a ``provider``/``adjusted_flag`` label present → UNQUALIFIED /
       ``PROVIDER_LABEL_ONLY`` (P01.01); otherwise UNCAPTURED / ``NO_RECEIPT``.
    4. receipt but no ``endpoint`` or no ``field_convention`` → UNQUALIFIED /
       ``UNIDENTIFIED_CONVENTION`` (P01.01).
    5. a never-admissible convention → UNQUALIFIED with the per-convention code
       (``CUMULATIVE_FACTOR_NOT_AS_OBSERVED`` / ``CURRENT_SHARE_CASH_NOT_AS_DECLARED``
       / ``ADJUSTED_SERIES_NOT_AN_EVENT``) (P01.04).
    6. ``response == empty`` → NO_ACTION_IN_QUALIFIED_RESPONSE / ``QUALIFIED_EMPTY``
       (P01.03) — authoritative absence, deliberately NOT ``UNCAPTURED``.
    7. ``response is None`` → UNCAPTURED / ``NO_RESPONSE``.
    8. otherwise CONFIRMED / ``AS_OBSERVED`` — reachable ONLY here.

    With ``registry`` given (a :class:`Registry`), the source checks run AFTER
    rule 1 and BEFORE rule 2: an unknown ``dataset_id`` → UNQUALIFIED /
    ``UNREGISTERED_SOURCE``; a row whose status is not PRODUCED (PROPOSED,
    RETIRED) → UNQUALIFIED / ``SOURCE_NOT_PRODUCED`` (R00.04: the PROPOSED
    Tiingo contracts stay PROPOSED until their original owner produces them).
    The discontinuity rule outranks them because an inference from a produced
    source's price path is still an inference; they outrank the rights rule
    because a not-yet-produced source cannot witness anything, rights-limited
    or not.
    """
    if not isinstance(observation, Mapping):
        raise TypeError(
            f"observation must be a Mapping, got {type(observation).__name__}"
        )
    known = set(ACTION_INPUT_FIELDS) | set(ACTION_INPUT_OPTIONAL_FIELDS)
    unknown = sorted(set(observation) - known)
    if unknown:
        raise ValueError(
            f"unknown observation key(s) {unknown}; action observations carry "
            f"exactly {sorted(known)} — an ignored key is how a vendor label "
            "hides beside a qualifying-looking dict"
        )
    missing = [name for name in ACTION_INPUT_FIELDS if name not in observation]
    if missing:
        raise ValueError(f"missing required observation key(s) {missing}")

    dataset_id = observation["dataset_id"]
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError(f"dataset_id must be a non-empty string, got {dataset_id!r}")
    endpoint = observation["endpoint"]
    if endpoint is not None and (not isinstance(endpoint, str) or not endpoint.strip()):
        raise ValueError(f"endpoint must be a non-empty string or None, got {endpoint!r}")
    field_convention = observation["field_convention"]
    if field_convention is not None and field_convention not in ACTION_FIELD_CONVENTIONS:
        raise ValueError(
            f"field_convention {field_convention!r} is not one of "
            f"({', '.join(ACTION_FIELD_CONVENTIONS)})"
        )
    receipt = observation["receipt"]
    if receipt is not None and (
        not isinstance(receipt, str) or not receipt.strip()
    ):
        raise ValueError(
            f"receipt must be the exact original receipt id/digest or None, "
            f"got {receipt!r}"
        )
    origin = observation["origin"]
    if origin not in ACTION_INPUT_ORIGINS:
        raise ValueError(
            f"origin {origin!r} is not one of ({', '.join(ACTION_INPUT_ORIGINS)})"
        )
    response = observation["response"]
    if response is not None and response not in ACTION_INPUT_RESPONSES:
        raise ValueError(
            f"response {response!r} is not one of (events, empty, None)"
        )
    rights_limited = observation["rights_limited"]
    if not isinstance(rights_limited, bool):
        raise ValueError(
            f"rights_limited must be a bool, got {type(rights_limited).__name__} "
            f"{rights_limited!r} — a truthiness coercion would invert the author's "
            "meaning (the point_in_time_corporate_actions precedent)"
        )
    provider = observation.get("provider")
    if provider is not None and (
        not isinstance(provider, str) or not provider.strip()
    ):
        raise ValueError(f"provider must be a non-empty string or None, got {provider!r}")
    adjusted_flag = observation.get("adjusted_flag")
    if adjusted_flag is not None and not isinstance(adjusted_flag, bool):
        raise ValueError(
            f"adjusted_flag must be a bool or None, got {adjusted_flag!r}"
        )

    def verdict(status: ActionInputStatus, reason: str) -> ActionInputVerdict:
        return ActionInputVerdict(
            status=status, reason=reason, dataset_id=dataset_id, receipt=receipt
        )

    # Rule 1 — the price path is never an event witness, receipt or not (P01.02).
    if origin == "price_discontinuity":
        return verdict(ActionInputStatus.SUSPECTED, "DISCONTINUITY_INFERRED")

    # Registry step — source checks run after rule 1, before rule 2: a produced
    # source is a precondition for ANY capture question below.
    if registry is not None:
        if not isinstance(registry, Registry):
            raise TypeError(
                f"registry must be a Registry, got {type(registry).__name__}"
            )
        contract = registry.get(dataset_id)
        if contract is None:
            return verdict(ActionInputStatus.UNQUALIFIED, "UNREGISTERED_SOURCE")
        if contract.status is not DatasetStatus.PRODUCED:
            # PROPOSED stays PROPOSED until its original owner produces it
            # (R00.04); RETIRED no longer exists to witness new events.  Both
            # refuse under one code: the source is not (currently) produced.
            return verdict(ActionInputStatus.UNQUALIFIED, "SOURCE_NOT_PRODUCED")

    # Rule 2 — rights-limited capture (an unsupported family, D00.D3) is never
    # coerced into one (P01.03); refusal precedes the receipt/label questions.
    if rights_limited:
        return verdict(ActionInputStatus.UNCAPTURED, "RIGHTS_LIMITED")

    # Rule 3 — no receipt: a provider label is the exact thing P01.01 exists to
    # refuse; with no label either, the event was simply never captured.
    if receipt is None:
        if provider is not None or adjusted_flag is not None:
            return verdict(ActionInputStatus.UNQUALIFIED, "PROVIDER_LABEL_ONLY")
        return verdict(ActionInputStatus.UNCAPTURED, "NO_RECEIPT")

    # Rule 4 — a receipt must identify WHERE and IN WHAT CONVENTION it observed.
    if endpoint is None or field_convention is None:
        return verdict(ActionInputStatus.UNQUALIFIED, "UNIDENTIFIED_CONVENTION")

    # Rule 5 — derived quantities offered as events (P01.04).
    refusal = _CONVENTION_REFUSALS.get(field_convention)
    if refusal is not None:
        return verdict(ActionInputStatus.UNQUALIFIED, refusal)

    # Rule 6 — a qualified, authoritative empty is absence, not defect (P01.03).
    if response == "empty":
        return verdict(
            ActionInputStatus.NO_ACTION_IN_QUALIFIED_RESPONSE, "QUALIFIED_EMPTY"
        )

    # Rule 7 — the capture never answered.
    if response is None:
        return verdict(ActionInputStatus.UNCAPTURED, "NO_RESPONSE")

    # Rule 8 — the only door to CONFIRMED: as-observed, receipted, produced.
    return verdict(ActionInputStatus.CONFIRMED, "AS_OBSERVED")
