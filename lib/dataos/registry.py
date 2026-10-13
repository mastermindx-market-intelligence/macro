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
from enum import Enum
from pathlib import Path
from typing import Any

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
