"""C2 coverage proof: predeclared thresholds proven from a coverage manifest.

Acceptance case A36 — "predeclare issuer/period/field thresholds; prove them
by manifest, not ticker loop count."  This module uses no network, no store
and no wall clock, and imports nothing from ``scripts/``.  The one repository
file it opens itself is the file named by the thresholds' ``freeze_ref``,
whose bytes it hashes for the report; the frozen thresholds config, the
governed metric catalog and the ``fundamental_forensics.coverage_manifest/v1``
document all arrive through its parameters, and the output is a
``fundamental_forensics.coverage_proof/v1`` report plus a fixed print block.

Membership comes only from ``issuers[]`` (``tier_assigned``); a ticker loop,
distinct cell CIKs, or ``cell.tier`` tags never define membership.  Core
members are every issuer whose ``tier_assigned`` is ``core`` or ``deep``;
deep members are the ``deep`` subset.  Field-presence denominators follow
membership, not the manifest's own rollup: deep fields are the deep members'
metric cells over the deep periods, core fields are all core members'
(including deep) over the core periods.

A shortfall is reported, never hidden, and never repaired by editing a
target, a band, or a window.

One declared legacy alias exists (seat ruling K-V1A-R1): a ``package.<role>``
field_id whose role is one of the thresholds config's ``required_package_roles``
is rewritten to ``package:<role>`` before any duplicate check or cell indexing,
counted under ``field_id_aliases_applied``, and reported as the
``legacy_field_id_alias`` acceptance blocker.  The alias exists only so a
census draft can be measured; an attested acceptance manifest must use the
canonical vocabulary, and every other dotted or unknown ``field_id`` is still
refused.

Review-lane rulings (V1-a r2, 2026-10-19) tighten what may ever count toward
a tier and what blocks acceptance: an issuer counts toward a tier only when
its band for that tier's scope is ``complete`` and its failed-field list is
empty; a withheld formula metric fails its issuer for the pass decision
(reason ``formula_inputs_absent``); an issuer with no applicable fields never
passes; the statuses ``stale``, ``failed_extraction`` and ``incomparable``
count in ``applicable``, fail the issuer and are reported in their own
counts; a present cell carrying a reason is refused; the manifest's census
identity, the cells' source generations and the freeze reference are checked
and any disagreement is an acceptance blocker; orphan cells and rollup
mismatches block acceptance; a metric cell outside the declared windows is
an orphan, never silently dropped; core periods outside the deep periods are
refused at load.

Review-lane rulings (V1-a r3, 2026-10-19) make the prover accept the real
census draft's present cells and bind the proof to byte-computed identity:
a present cell may carry ``reason_code`` ``None``, ``""`` or ``"present"``
(anything else is still refused); ``freeze_ref`` must be a relative POSIX
path — no leading slash, no backslash, no ``..`` or empty segment — whose
resolved path lies inside the repository root and names a regular file, and
a rule break adds the ``freeze_ref_invalid`` blocker while the report still
runs (the report carries the declared relative path, its validity, its
existence and its bytes' sha256 — never an absolute host path); a missing or
ill-typed manifest rollup field blocks through ``rollup_mismatch`` with
reason ``rollup_field_invalid`` instead of skipping the comparison; the
manifest arrives as bytes and the prover itself computes every sha256 it
reports, so a caller-supplied hash is never trusted; the draft identity is
the manifest bytes' sha256 for a draft and the declared top-level
``manifest_draft_sha256`` (64 lowercase hex) otherwise, and the thresholds'
``manifest_draft_sha256_prefix`` must always prefix it — the pin check is
never skipped; and the orphan window check covers every field family, with
a package cell on a member that is not deep an orphan.

Review-lane rulings (V1-a r4, 2026-10-19) close a wildcard escape, widen
the deep-only orphan rule and mark the attestation trust boundary.  Only the
windowless families — packet, journey and specialist — are exempt from the
window test: a metric, package or statement cell carrying the wildcard
period is an orphan under ``windowless_period_on_windowed_family``.  The
deep-only families are package, statement, specialist, packet and journey —
the frozen deep tier's own component set — and any of their cells on a
member that is not deep is an orphan under ``deep_component_not_deep_member``
(generalizing r3's package-only reason, which was never merged).  A
non-draft manifest's draft identity is declared, never proved: bytes alone
cannot show which draft an attestation covers, so the basis reports
``declared_unverified`` for every non-draft with
``draft_identity_trust: "attestation_required"`` — the attestation is what
must carry the proof — and a manifest that declares its own
``manifest_draft_sha256_prefix`` must declare the thresholds' pin exactly, a
difference being the ``manifest_draft_sha256_prefix_declared`` census
identity mismatch.

Seat ruling BLOCKER-1 (2026-10-19) makes the proof say how much of a
``complete`` band rests on labelled cells.  Census writers stamp three cell
labels, checked with the rest of the cell: ``na_basis`` on a
``not_applicable`` cell (``kernel`` — the kernel's own N/A, and the reading
of an absent basis — ``not_presented_item`` or ``class_policy``), and
``qualifier`` or ``derivation`` on a ``present`` cell, each carried by a
versioned ``qualifier_policy`` / ``derivation_policy`` (``<id>/<version>``).
A label on the wrong status, an unknown basis, an empty label or a missing
policy is refused with its own typed code; a JSON null is an absent label.
Over each tier's metric scope the proof counts ``present_strict``,
``present_qualified``, ``present_composed``, ``na_kernel``,
``na_not_presented`` and ``na_class`` (a cell with both present labels
counts in both labelled counts, never in strict), plus, for the deep tier,
``component_labelled`` over the deep component cells.  An issuer is
``complete_strict`` for a tier when it passes that tier (band ``complete``
and no failed field; seat ruling V1A-S1) and it has no qualified, composed,
not-presented or class-policy cell (and, for deep, no labelled component).
``complete_strict`` is reported per tier and per issuer and printed beside
``complete``; per tier it never exceeds ``pass``.  It is reporting only: a labelled
present cell is present exactly as before, an N/A of any basis leaves the
applicable denominator exactly as before, and pass, target, band, rate,
failed fields and every acceptance blocker are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import yaml

from .metric_registry import CATALOG_SCHEMA, FORMULAS_SCHEMA
from .models import canonical_json, utc_text


THRESHOLDS_SCHEMA = "fundamental_forensics.coverage_thresholds/v1"
MANIFEST_SCHEMA = "fundamental_forensics.coverage_manifest/v1"
PROOF_SCHEMA = "fundamental_forensics.coverage_proof/v1"

FROZEN_DEEP_TARGET = 250
FROZEN_CORE_TARGET = 1000

HARD_MAX_MANIFEST_BYTES = 256 * 1024 * 1024
HARD_MAX_CELLS = 2_000_000
HARD_MAX_ISSUERS = 20_000

WILDCARD_PERIOD = "*"
STATE_PRESENT = "present"
STATE_NOT_APPLICABLE = "not_applicable"
STATE_ABSENT = "absent"
STATE_STALE = "stale"
STATE_FAILED_EXTRACTION = "failed_extraction"
STATE_INCOMPARABLE = "incomparable"
REASON_CELL_MISSING = "cell_missing"
REASON_FORMULA_INPUTS_ABSENT = "formula_inputs_absent"
REASON_ORPHAN_CIK = "cik_not_member"
REASON_ORPHAN_WINDOW = "period_outside_windows"
REASON_ORPHAN_WINDOWLESS = "windowless_period_on_windowed_family"
REASON_ORPHAN_DEEP_COMPONENT = "deep_component_not_deep_member"
NO_APPLICABLE_FIELDS_BAND = "no_applicable_fields"
COMPLETE_BAND = "complete"

# Seat ruling BLOCKER-1 (2026-10-19): the N/A bases a census writer may stamp
# and the count each lands in.  An absent ``na_basis`` is the kernel's own
# N/A (legacy manifests carry none).
NA_BASIS_KERNEL = "kernel"
NA_BASIS_NOT_PRESENTED = "not_presented_item"
NA_BASIS_CLASS = "class_policy"
_NA_BASIS_COUNT_KEYS: Mapping[str, str] = {
    NA_BASIS_KERNEL: "na_kernel",
    NA_BASIS_NOT_PRESENTED: "na_not_presented",
    NA_BASIS_CLASS: "na_class",
}
# Present-cell labels and the versioned policy key each one requires.
_PRESENT_LABELS = (("qualifier", "qualifier_policy"), ("derivation", "derivation_policy"))
_LABEL_COUNT_KEYS = (
    "present_strict",
    "present_qualified",
    "present_composed",
    "na_kernel",
    "na_not_presented",
    "na_class",
)
# The labelled counts that keep an otherwise complete issuer out of
# ``complete_strict``.
_NON_STRICT_COUNT_KEYS = (
    "present_qualified",
    "present_composed",
    "na_not_presented",
    "na_class",
)
_POLICY_ID = re.compile(r"^\S+/\S+$")

# The repository root a ``freeze_ref`` is declared against.  Deriving it from
# this module's location keeps the check a pure tree lookup: no network, no
# store, no wall-clock read.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# The single declared legacy field_id alias (seat ruling K-V1A-R1): the census
# draft spells its package cells "package.<role>" where the frozen vocabulary
# is "package:<role>".  The accepted roles are never listed here; they come
# from the thresholds config's required_package_roles.
LEGACY_PACKAGE_ALIAS_PREFIX = "package."
LEGACY_FIELD_ID_ALIAS_BLOCKER = "legacy_field_id_alias"

_CIK = re.compile(r"^[0-9]{10}$")
_METRIC_FIELD = re.compile(r"^metric:\S+$")
_PACKAGE_FIELD = re.compile(r"^package:\S+$")
_STATEMENT_FIELD = re.compile(r"^statement:\S+$")
_SPECIALIST_FIELD = re.compile(r"^specialist:PK[0-9]{2}$")
_BARE_FIELDS = frozenset({"packet", "journey"})
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

# Manifest status -> proof state.  ``slot_absent`` is never turned into
# ``not_applicable``; only an explicit ``not_applicable`` leaves the
# applicable denominator.  ``stale``, ``failed_extraction`` and
# ``incomparable`` (ruling V1-a r2) keep their own names: each counts in
# ``applicable``, fails the issuer for the pass decision, and is reported in
# its own count — never merged into ``absent``.
_STATUS_STATES: Mapping[str, str] = {
    "present": STATE_PRESENT,
    "not_applicable": STATE_NOT_APPLICABLE,
    "absent": STATE_ABSENT,
    "slot_absent": STATE_ABSENT,
    "stale": STATE_STALE,
    "failed_extraction": STATE_FAILED_EXTRACTION,
    "incomparable": STATE_INCOMPARABLE,
}

# Per-state count keys shared by issuer cell tallies and component buckets.
_CELL_STATE_KEYS = (
    STATE_PRESENT,
    STATE_ABSENT,
    STATE_NOT_APPLICABLE,
    STATE_STALE,
    STATE_FAILED_EXTRACTION,
    STATE_INCOMPARABLE,
)
_COMPONENT_BUCKET_KEYS = _CELL_STATE_KEYS + ("missing",)

_THRESHOLD_KEYS = frozenset(
    {
        "schema",
        "thresholds_id",
        "freeze_ref",
        "census_identity",
        "metric_catalog_id",
        "metric_count",
        "direct_metric_count",
        "formula_metric_count",
        "tiers",
        "field_presence_bands",
    }
)
_CENSUS_IDENTITY_KEYS = frozenset(
    {"source_generation_id", "cutoff_at", "manifest_draft_sha256_prefix"}
)
_DEEP_TIER_KEYS = frozenset(
    {
        "target",
        "periods",
        "required_package_roles",
        "required_statements",
        "specialist_packs",
        "require_packet",
        "require_journey",
    }
)
_CORE_TIER_KEYS = frozenset({"target", "periods"})


class CoverageProofError(ValueError):
    """An input refusal with a machine-readable ``code``."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class CoverageThresholds:
    """The frozen, predeclared coverage thresholds plus their content hash."""

    schema: str
    thresholds_id: str
    freeze_ref: str
    census_identity: Mapping[str, Any]
    metric_catalog_id: str
    metric_count: int
    direct_metric_count: int
    formula_metric_count: int
    tiers: Mapping[str, Any]
    field_presence_bands: tuple[tuple[str, float], ...]
    content_sha256: str

    @property
    def deep_target(self) -> int:
        return int(self.tiers["deep"]["target"])

    @property
    def core_target(self) -> int:
        return int(self.tiers["core"]["target"])

    @property
    def deep_periods(self) -> tuple[str, ...]:
        return tuple(self.tiers["deep"]["periods"])

    @property
    def core_periods(self) -> tuple[str, ...]:
        return tuple(self.tiers["core"]["periods"])

    @property
    def band_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.field_presence_bands)

    @property
    def package_alias_roles(self) -> frozenset[str]:
        """The only roles whose legacy ``package.<role>`` spelling is aliased."""
        return frozenset(self.tiers["deep"]["required_package_roles"])

    def band_for_rate(self, rate: float | None) -> str:
        """First band whose ``min_rate`` is <= rate; null rate has no band."""
        if rate is None:
            return NO_APPLICABLE_FIELDS_BAND
        for name, minimum in self.field_presence_bands:
            if minimum <= rate:
                return name
        # Unreachable while the last band sits at 0.0, which band checks enforce.
        return self.field_presence_bands[-1][0]


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


def _shape(problem: str) -> CoverageProofError:
    return CoverageProofError("thresholds_shape", problem)


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _shape(f"{field} must be a non-empty string")
    return value


def _require_count(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise _shape(f"{field} must be a positive integer")
    return int(value)


def _require_flag(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise _shape(f"{field} must be a boolean")
    return value


def _require_names(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _shape(f"{field} must be a non-empty list")
    names = tuple(_require_text(item, f"{field}[]") for item in value)
    if len(set(names)) != len(names):
        raise _shape(f"{field} cannot contain duplicate entries")
    return names


def _check_exact_keys(
    value: Mapping[str, Any], field: str, required: frozenset[str]
) -> None:
    unknown = sorted(set(value) - required)
    missing = sorted(required - set(value))
    if unknown:
        raise _shape(f"{field} contains unsupported key(s): {', '.join(unknown)}")
    if missing:
        raise _shape(f"{field} omits required key(s): {', '.join(missing)}")


def _parse_bands(value: Any) -> tuple[tuple[str, float], ...]:
    def band_problem(problem: str) -> CoverageProofError:
        return CoverageProofError("band_shape", f"field_presence_bands {problem}")

    if not isinstance(value, list) or not value:
        raise band_problem("must be a non-empty list")
    band_keys = frozenset({"band", "min_rate"})
    bands: list[tuple[str, float]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise band_problem(f"[{index}] must be an object")
        unknown = sorted(set(item) - band_keys)
        missing = sorted(band_keys - set(item))
        if unknown or missing:
            raise band_problem(
                f"[{index}] must have exactly band and min_rate"
                + (f"; unsupported: {', '.join(unknown)}" if unknown else "")
                + (f"; missing: {', '.join(missing)}" if missing else "")
            )
        name = item["band"]
        if not isinstance(name, str) or not name.strip():
            raise band_problem(f"[{index}].band must be a non-empty string")
        rate = item["min_rate"]
        if isinstance(rate, bool) or not isinstance(rate, (int, float)):
            raise band_problem(f"[{index}].min_rate must be numeric")
        rate = float(rate)
        if not 0.0 <= rate <= 1.0:
            raise band_problem(f"[{index}].min_rate must lie in [0, 1]")
        bands.append((name.strip(), rate))
    names = [name for name, _ in bands]
    if len(set(names)) != len(names):
        raise band_problem("cannot contain duplicate band names")
    for (name, rate), (_, next_rate) in zip(bands, bands[1:]):
        if not rate > next_rate:
            raise band_problem(
                f"must be strictly descending by min_rate at {name}"
            )
    if bands[0][0] != "complete" or bands[0][1] != 1.0:
        raise band_problem("the first band must be complete at 1.0")
    if bands[-1][1] != 0.0:
        raise band_problem("the last band must sit at 0.0")
    return tuple(bands)


def _thresholds_from_raw(
    raw: Any, content_sha256: str, *, enforce_frozen_targets: bool
) -> CoverageThresholds:
    if not isinstance(raw, Mapping):
        raise _shape("thresholds must be an object")
    _check_exact_keys(raw, "thresholds", _THRESHOLD_KEYS)
    schema = _require_text(raw["schema"], "thresholds.schema")
    if schema != THRESHOLDS_SCHEMA:
        raise _shape(f"thresholds.schema must equal {THRESHOLDS_SCHEMA}")
    thresholds_id = _require_text(raw["thresholds_id"], "thresholds.thresholds_id")
    freeze_ref = _require_text(raw["freeze_ref"], "thresholds.freeze_ref")

    census_raw = raw["census_identity"]
    if not isinstance(census_raw, Mapping):
        raise _shape("thresholds.census_identity must be an object")
    _check_exact_keys(census_raw, "thresholds.census_identity", _CENSUS_IDENTITY_KEYS)
    census_identity = {
        key: _require_text(census_raw[key], f"thresholds.census_identity.{key}")
        for key in ("source_generation_id", "cutoff_at", "manifest_draft_sha256_prefix")
    }

    metric_catalog_id = _require_text(
        raw["metric_catalog_id"], "thresholds.metric_catalog_id"
    )
    metric_count = _require_count(raw["metric_count"], "thresholds.metric_count")
    direct_count = _require_count(
        raw["direct_metric_count"], "thresholds.direct_metric_count"
    )
    formula_count = _require_count(
        raw["formula_metric_count"], "thresholds.formula_metric_count"
    )
    if direct_count + formula_count != metric_count:
        raise _shape(
            "thresholds metric counts must satisfy "
            "direct_metric_count + formula_metric_count == metric_count"
        )

    tiers_raw = raw["tiers"]
    if not isinstance(tiers_raw, Mapping):
        raise _shape("thresholds.tiers must be an object")
    unknown_tiers = sorted(set(tiers_raw) - {"deep", "core"})
    if unknown_tiers:
        raise _shape(f"thresholds.tiers contains unsupported tier(s): {', '.join(unknown_tiers)}")
    missing_tiers = sorted({"deep", "core"} - set(tiers_raw))
    if missing_tiers:
        raise _shape(f"thresholds.tiers omits required tier(s): {', '.join(missing_tiers)}")

    deep_raw = tiers_raw["deep"]
    if not isinstance(deep_raw, Mapping):
        raise _shape("thresholds.tiers.deep must be an object")
    _check_exact_keys(deep_raw, "thresholds.tiers.deep", _DEEP_TIER_KEYS)
    core_raw = tiers_raw["core"]
    if not isinstance(core_raw, Mapping):
        raise _shape("thresholds.tiers.core must be an object")
    _check_exact_keys(core_raw, "thresholds.tiers.core", _CORE_TIER_KEYS)

    deep_target = _require_count(deep_raw["target"], "thresholds.tiers.deep.target")
    core_target = _require_count(core_raw["target"], "thresholds.tiers.core.target")
    if enforce_frozen_targets and (
        deep_target != FROZEN_DEEP_TARGET or core_target != FROZEN_CORE_TARGET
    ):
        raise CoverageProofError(
            "frozen_target",
            f"coverage targets are frozen at deep={FROZEN_DEEP_TARGET} and "
            f"core={FROZEN_CORE_TARGET}; refusing deep={deep_target} "
            f"core={core_target}",
        )

    tiers: dict[str, Any] = {
        "deep": {
            "target": deep_target,
            "periods": _require_names(deep_raw["periods"], "thresholds.tiers.deep.periods"),
            "required_package_roles": _require_names(
                deep_raw["required_package_roles"],
                "thresholds.tiers.deep.required_package_roles",
            ),
            "required_statements": _require_names(
                deep_raw["required_statements"],
                "thresholds.tiers.deep.required_statements",
            ),
            "specialist_packs": _require_names(
                deep_raw["specialist_packs"],
                "thresholds.tiers.deep.specialist_packs",
            ),
            "require_packet": _require_flag(
                deep_raw["require_packet"], "thresholds.tiers.deep.require_packet"
            ),
            "require_journey": _require_flag(
                deep_raw["require_journey"], "thresholds.tiers.deep.require_journey"
            ),
        },
        "core": {
            "target": core_target,
            "periods": _require_names(core_raw["periods"], "thresholds.tiers.core.periods"),
        },
    }

    # Ruling V1-a r2 (F6): core periods outside the deep periods would be a
    # silent window drop — every core period must also be a deep period.
    core_outside_deep = [
        name for name in tiers["core"]["periods"]
        if name not in set(tiers["deep"]["periods"])
    ]
    if core_outside_deep:
        raise CoverageProofError(
            "period_windows",
            "thresholds.tiers.core.periods must be a subset of "
            f"thresholds.tiers.deep.periods; outside: {', '.join(core_outside_deep)}",
        )

    return CoverageThresholds(
        schema=schema,
        thresholds_id=thresholds_id,
        freeze_ref=freeze_ref,
        census_identity=census_identity,
        metric_catalog_id=metric_catalog_id,
        metric_count=metric_count,
        direct_metric_count=direct_count,
        formula_metric_count=formula_count,
        tiers=tiers,
        field_presence_bands=_parse_bands(raw["field_presence_bands"]),
        content_sha256=content_sha256,
    )


def thresholds_from_mapping(
    mapping: Any, *, enforce_frozen_targets: bool = True
) -> CoverageThresholds:
    """Check a thresholds mapping; tests may relax the frozen target check."""
    if not isinstance(mapping, Mapping):
        raise _shape("thresholds must be an object")
    digest = hashlib.sha256(canonical_json(dict(mapping)).encode("utf-8")).hexdigest()
    return _thresholds_from_raw(
        mapping, digest, enforce_frozen_targets=enforce_frozen_targets
    )


def load_thresholds(path: str | Path) -> CoverageThresholds:
    """Read the frozen thresholds JSON and hash its exact file bytes."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise _shape(f"cannot read thresholds file: {exc}") from exc
    digest = hashlib.sha256(data).hexdigest()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _shape(f"thresholds file is not decodable JSON: {exc}") from exc
    return _thresholds_from_raw(raw, digest, enforce_frozen_targets=True)


# ---------------------------------------------------------------------------
# Metric sets
# ---------------------------------------------------------------------------


def _read_yaml_mapping(path: str | Path, label: str) -> Mapping[str, Any]:
    def drift(problem: str) -> CoverageProofError:
        return CoverageProofError("catalog_drift", f"{label} {problem}")

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise drift(f"cannot be read: {exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise drift(f"is not parseable YAML: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise drift("must be a YAML mapping")
    return raw


def load_metric_sets(
    catalog_path: str | Path,
    formulas_path: str | Path,
    thresholds: CoverageThresholds | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split the governed catalog into direct and formula metric ids.

    Formula ids are the ``metric_id``s under ``formulas:`` in the formulas
    pack; direct ids are the catalog's metric ids minus the formula ids.  The
    ids are read from the catalog files the way the registry loader reads
    them — never from a copied hard-coded list.
    """
    catalog_raw = _read_yaml_mapping(catalog_path, "metric catalog")
    formulas_raw = _read_yaml_mapping(formulas_path, "metric formulas")

    def drift(problem: str) -> CoverageProofError:
        return CoverageProofError("catalog_drift", problem)

    if catalog_raw.get("schema") != CATALOG_SCHEMA:
        raise drift(f"metric catalog schema must equal {CATALOG_SCHEMA}")
    if formulas_raw.get("schema") != FORMULAS_SCHEMA:
        raise drift(f"metric formulas schema must equal {FORMULAS_SCHEMA}")

    catalog_id = catalog_raw.get("catalog_id")
    if not isinstance(catalog_id, str) or not catalog_id:
        raise drift("metric catalog must declare a catalog_id")

    def metric_ids_from(entries: Any, label: str) -> list[str]:
        if not isinstance(entries, list) or not entries:
            raise drift(f"{label} must be a non-empty list")
        ids: list[str] = []
        for index, item in enumerate(entries):
            if not isinstance(item, Mapping):
                raise drift(f"{label}[{index}] must be an object")
            metric_id = item.get("metric_id")
            if not isinstance(metric_id, str) or not metric_id:
                raise drift(f"{label}[{index}].metric_id must be a non-empty string")
            ids.append(metric_id)
        if len(set(ids)) != len(ids):
            raise drift(f"{label} contains duplicate metric_id entries")
        return ids

    catalog_ids = metric_ids_from(catalog_raw.get("metrics"), "catalog metrics")
    formula_ids = metric_ids_from(formulas_raw.get("formulas"), "catalog formulas")
    unknown = sorted(set(formula_ids) - set(catalog_ids))
    if unknown:
        raise drift(
            f"formula metrics absent from the catalog: {', '.join(unknown)}"
        )
    direct_ids = sorted(set(catalog_ids) - set(formula_ids))
    formula_ids_sorted = sorted(formula_ids)

    if thresholds is not None:
        if len(catalog_ids) != thresholds.metric_count:
            raise drift(
                f"catalog exposes {len(catalog_ids)} metrics; thresholds "
                f"predeclare {thresholds.metric_count}"
            )
        if len(direct_ids) != thresholds.direct_metric_count:
            raise drift(
                f"catalog exposes {len(direct_ids)} direct metrics; thresholds "
                f"predeclare {thresholds.direct_metric_count}"
            )
        if len(formula_ids_sorted) != thresholds.formula_metric_count:
            raise drift(
                f"catalog exposes {len(formula_ids_sorted)} formula metrics; "
                f"thresholds predeclare {thresholds.formula_metric_count}"
            )
        if catalog_id != thresholds.metric_catalog_id:
            raise drift(
                f"catalog id {catalog_id!r} differs from the predeclared "
                f"{thresholds.metric_catalog_id!r}"
            )
    return tuple(direct_ids), tuple(formula_ids_sorted)


# ---------------------------------------------------------------------------
# Manifest reading
# ---------------------------------------------------------------------------


def _is_canonical_field_id(field_id: str) -> bool:
    return bool(
        _METRIC_FIELD.fullmatch(field_id)
        or _PACKAGE_FIELD.fullmatch(field_id)
        or _STATEMENT_FIELD.fullmatch(field_id)
        or _SPECIALIST_FIELD.fullmatch(field_id)
        or field_id in _BARE_FIELDS
    )


def _is_windowless_field_id(field_id: Any) -> bool:
    """True for the windowless families: packet, journey and specialist.

    Ruling V1-a r4 (R1): these three families — and only they — are exempt
    from the window test; their cells carry the wildcard period by
    cell-shape law.
    """
    return isinstance(field_id, str) and (
        field_id in _BARE_FIELDS or field_id.startswith("specialist:")
    )


def _is_deep_only_field_id(field_id: Any) -> bool:
    """True for the five deep-only component families (ruling V1-a r4, R2).

    The frozen deep tier is assembled from package roles, statements,
    specialist packs, packet and journey; the core tier declares periods
    only, so a cell of any of these families on a member that is not deep is
    a deep component outside its tier.  Package is matched in both the
    canonical ``package:<role>`` and the accepted legacy ``package.<role>``
    spelling; by the time cells reach the orphan scan, ``_index_cells`` has
    already refused every dotted spelling whose role is not one of the
    thresholds' alias roles.
    """
    return isinstance(field_id, str) and (
        field_id.startswith("package:")
        or field_id.startswith(LEGACY_PACKAGE_ALIAS_PREFIX)
        or field_id.startswith("statement:")
        or _is_windowless_field_id(field_id)
    )


def _check_cell_shape(
    cell: Any,
    position: int,
    package_alias_roles: frozenset[str] = frozenset(),
) -> tuple[str, str, str, bool]:
    """Validate one cell; return ``(cik, period_id, canonical field_id, aliased)``.

    The declared legacy alias is applied here, before any duplicate check or
    cell indexing: ``package.<role>`` becomes ``package:<role>`` exactly when
    ``role`` is one of ``package_alias_roles`` (the thresholds config's
    required_package_roles).  Every other dotted or unknown ``field_id`` is
    refused below exactly as it would be without the alias.
    """
    def shape(problem: str) -> CoverageProofError:
        return CoverageProofError("cell_shape", f"cells[{position}] {problem}")

    if not isinstance(cell, Mapping):
        raise shape("must be an object")
    cik = cell.get("cik")
    if not isinstance(cik, str) or not _CIK.fullmatch(cik):
        raise shape("cik must be a 10-digit string")
    period_id = cell.get("period_id")
    if not isinstance(period_id, str):
        raise shape("period_id must be a string")
    field_id = cell.get("field_id")
    aliased = False
    if (
        isinstance(field_id, str)
        and not _is_canonical_field_id(field_id)
        and field_id.startswith(LEGACY_PACKAGE_ALIAS_PREFIX)
    ):
        role = field_id[len(LEGACY_PACKAGE_ALIAS_PREFIX):]
        if role and role in package_alias_roles:
            field_id = f"package:{role}"
            aliased = True
    if not isinstance(field_id, str) or not _is_canonical_field_id(field_id):
        raise shape(
            f"field_id must be metric:<id>, package:<role>, statement:<kind>, "
            f"specialist:<PKnn>, packet or journey; got {field_id!r}"
        )
    if (
        field_id in _BARE_FIELDS or field_id.startswith("specialist:")
    ) and period_id != WILDCARD_PERIOD:
        raise shape(f"{field_id} cells must use period_id {WILDCARD_PERIOD!r}")
    status = cell.get("status")
    if not isinstance(status, str):
        raise shape("status must be a string")
    if status not in _STATUS_STATES:
        raise CoverageProofError(
            "status_vocabulary",
            f"cells[{position}] has an unsupported status: {status!r}",
        )
    if status == "present":
        # Ruling V1-a r3 (G1): the real census draft stamps its present cells
        # with reason_code "present" (or ""), so those two spellings — plus
        # an explicit null — are accepted.  Any other value on a present cell
        # is still refused with a typed code, never silently counted.
        reason = cell.get("reason_code")
        if reason is not None and reason not in ("", "present"):
            raise CoverageProofError(
                "present_cell_carries_reason",
                f"cells[{position}] is present but carries reason_code "
                f"{reason!r}; a present cell may carry no reason or "
                f"'present'",
            )
    _check_cell_labels(cell, status, position)
    source_generation_id = cell.get("source_generation_id")
    if not isinstance(source_generation_id, str) or not source_generation_id:
        raise shape(
            "source_generation_id must be a non-empty string; no coverage row "
            "without it"
        )
    return cik, period_id, field_id, aliased


def _check_cell_labels(cell: Mapping[str, Any], status: str, position: int) -> None:
    """Check the seat-ruling BLOCKER-1 labels on one cell.

    A key whose value is JSON null is an absent label.  ``na_basis`` belongs
    only to a ``not_applicable`` cell; ``qualifier`` and ``derivation`` only
    to a ``present`` cell, each with its versioned policy.  Every other extra
    key stays accepted and unread.
    """
    na_basis = cell.get("na_basis")
    if na_basis is not None:
        if status != "not_applicable":
            raise CoverageProofError(
                "na_basis_on_applicable_cell",
                f"cells[{position}] has status {status!r} but carries na_basis "
                f"{na_basis!r}; only a not_applicable cell may carry one",
            )
        if not isinstance(na_basis, str) or na_basis not in _NA_BASIS_COUNT_KEYS:
            raise CoverageProofError(
                "na_basis_vocabulary",
                f"cells[{position}] has an unsupported na_basis {na_basis!r}; "
                f"allowed: {', '.join(_NA_BASIS_COUNT_KEYS)}",
            )
    for label, policy_key in _PRESENT_LABELS:
        value = cell.get(label)
        policy = cell.get(policy_key)
        if value is None:
            if policy is not None:
                raise CoverageProofError(
                    f"{policy_key}_without_{label}",
                    f"cells[{position}] carries {policy_key} {policy!r} but no {label}",
                )
            continue
        if status != "present":
            raise CoverageProofError(
                "label_on_non_present_cell",
                f"cells[{position}] has status {status!r} but carries {label} "
                f"{value!r}; only a present cell may carry one",
            )
        if not isinstance(value, str) or not value.strip():
            raise CoverageProofError(
                f"{label}_shape",
                f"cells[{position}] {label} must be a non-empty string; got {value!r}",
            )
        if not isinstance(policy, str) or not _POLICY_ID.fullmatch(policy):
            raise CoverageProofError(
                f"{policy_key}_missing",
                f"cells[{position}] carries {label} {value!r} without a versioned "
                f"{policy_key} (<policy id>/<version>); got {policy!r}",
            )


def _index_cells(
    cells: Any, package_alias_roles: frozenset[str] = frozenset()
) -> tuple[dict[tuple[str, str, str], Mapping[str, Any]], int]:
    """Index cells by canonical ``(cik, period_id, field_id)``.

    Returns the index plus the count of legacy ``package.<role>`` field_ids
    rewritten to the canonical spelling.
    """
    if not isinstance(cells, list):
        raise CoverageProofError("manifest_limits", "manifest cells must be a list")
    if len(cells) > HARD_MAX_CELLS:
        raise CoverageProofError(
            "manifest_limits",
            f"manifest carries {len(cells)} cells; the hard limit is {HARD_MAX_CELLS}",
        )
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    aliases_applied = 0
    for position, cell in enumerate(cells):
        cik, period_id, field_id, aliased = _check_cell_shape(
            cell, position, package_alias_roles
        )
        if aliased:
            aliases_applied += 1
        key = (cik, period_id, field_id)
        if key in index:
            raise CoverageProofError(
                "duplicate_cell",
                f"cells[{position}] repeats (cik, period_id, field_id)={key}",
            )
        index[key] = cell
    return index, aliases_applied


def load_manifest(path: str | Path) -> bytes:
    """Read a coverage manifest file's bytes under the hard size limit.

    Ruling V1-a r3 (M4): the bytes — never a parsed document and never a
    caller-computed hash — are what ``prove_coverage`` takes.  The prover
    parses the bytes and computes the sha256 itself, so nothing about the
    manifest's identity is taken on the caller's word.  Every document-level
    refusal (schema, limits, cell shape, the legacy alias) happens inside
    ``prove_coverage``, with the thresholds' alias roles in hand.
    """
    try:
        size = Path(path).stat().st_size
    except OSError as exc:
        raise CoverageProofError(
            "manifest_undecodable", f"cannot read manifest file: {exc}"
        ) from exc
    if size > HARD_MAX_MANIFEST_BYTES:
        raise CoverageProofError(
            "manifest_oversize",
            f"manifest is {size} bytes; the hard limit is {HARD_MAX_MANIFEST_BYTES}",
        )
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise CoverageProofError(
            "manifest_undecodable", f"cannot read manifest file: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Freeze reference
# ---------------------------------------------------------------------------


def _freeze_ref_state(freeze_ref: str) -> dict[str, Any]:
    """Resolve ``freeze_ref`` against the repository root (rulings M1/M2).

    ``freeze_ref`` must be a relative POSIX path — no leading slash, no
    backslash, no ``..`` or empty segment — whose resolved path lies inside
    ``_REPO_ROOT.resolve()`` and names a regular file.  A rule break
    (including a directory or an escape from the root) is reported as
    ``valid=False`` and becomes the ``freeze_ref_invalid`` blocker; the proof
    still runs and reports.  A well-formed path naming nothing keeps
    ``freeze_ref_missing``.  The sha256 is over the file's exact bytes, or
    ``None`` when the path is invalid or missing; no absolute host path ever
    leaves this function.
    """
    valid = not freeze_ref.startswith("/") and "\\" not in freeze_ref and all(
        segment not in ("", "..") for segment in freeze_ref.split("/")
    )
    exists = False
    sha256: str | None = None
    if valid:
        root = _REPO_ROOT.resolve()
        resolved = (root / freeze_ref).resolve()
        if root not in resolved.parents:
            # A symlink whose target escapes the repository is a rule break,
            # not a missing file.
            valid = False
        else:
            try:
                if resolved.is_file():
                    exists = True
                    sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
                elif resolved.exists():
                    # Present but not a regular file (a directory, a device).
                    valid = False
            except OSError:
                pass
    return {"valid": valid, "exists": exists, "sha256": sha256}


# ---------------------------------------------------------------------------
# Proof
# ---------------------------------------------------------------------------


def _absent_reason(cell: Mapping[str, Any]) -> str:
    reason = cell.get("reason_code")
    if isinstance(reason, str) and reason:
        return reason
    status = cell.get("status")
    if isinstance(status, str) and status:
        return status
    return STATE_ABSENT


def _field_label(period_id: str, field_id: str, reason: str) -> str:
    return f"{period_id}/{field_id}:{reason}"


def _reason_of(label: str) -> str:
    return label.rsplit(":", 1)[1] if ":" in label else ""


def prove_coverage(
    manifest_bytes: bytes,
    thresholds: CoverageThresholds,
    direct_ids: Any,
    formula_ids: Any,
    *,
    proved_at: datetime,
) -> dict[str, Any]:
    """Recompute tier coverage from membership and required cells.

    Ruling V1-a r3 (M4): the manifest arrives as its exact bytes; this
    function parses them and computes the sha256 itself.  A parsed document
    or a caller-supplied hash is refused — nothing about the manifest's
    identity is taken on the caller's word.
    """
    if not isinstance(proved_at, datetime):
        raise CoverageProofError("naive_clock", "proved_at must be a datetime")
    if proved_at.tzinfo is None or proved_at.utcoffset() is None:
        raise CoverageProofError(
            "naive_clock", "proved_at must carry an explicit timezone"
        )
    if not isinstance(manifest_bytes, (bytes, bytearray)):
        raise CoverageProofError(
            "manifest_bytes",
            "prove_coverage takes the manifest's bytes; a parsed manifest or "
            "a caller-supplied sha256 is never accepted",
        )
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageProofError(
            "manifest_undecodable", f"manifest bytes are not decodable JSON: {exc}"
        ) from exc
    if not isinstance(manifest, Mapping):
        raise CoverageProofError("manifest_schema", "manifest must be an object")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise CoverageProofError(
            "manifest_schema",
            f"manifest schema must equal {MANIFEST_SCHEMA}; got "
            f"{manifest.get('schema')!r}",
        )
    issuers = manifest.get("issuers")
    if not isinstance(issuers, list):
        raise CoverageProofError("manifest_limits", "manifest issuers must be a list")
    if len(issuers) > HARD_MAX_ISSUERS:
        raise CoverageProofError(
            "manifest_limits",
            f"manifest carries {len(issuers)} issuers; the hard limit is "
            f"{HARD_MAX_ISSUERS}",
        )
    cells = manifest.get("cells")
    index, package_aliases_applied = _index_cells(
        cells, thresholds.package_alias_roles
    )

    direct = {mid for mid in direct_ids}
    formula = {mid for mid in formula_ids}
    overlap = sorted(direct & formula)
    if overlap:
        raise CoverageProofError(
            "catalog_drift",
            f"metric ids are both direct and formula: {', '.join(overlap)}",
        )
    all_metrics = tuple(sorted(direct | formula))

    # Membership comes only from issuers[]; tier_assigned is the sole authority.
    members: dict[str, Mapping[str, Any]] = {}
    deep_ciks: list[str] = []
    for position, issuer in enumerate(issuers):
        if not isinstance(issuer, Mapping):
            raise CoverageProofError(
                "manifest_limits", f"issuers[{position}] must be an object"
            )
        tier = issuer.get("tier_assigned")
        if tier not in ("core", "deep"):
            raise CoverageProofError(
                "tier_vocabulary",
                f"issuers[{position}] has an unsupported tier_assigned: {tier!r}",
            )
        cik = issuer.get("cik")
        if not isinstance(cik, str) or not _CIK.fullmatch(cik):
            raise CoverageProofError(
                "cell_shape", f"issuers[{position}].cik must be a 10-digit string"
            )
        if cik in members:
            raise CoverageProofError(
                "duplicate_cell", f"issuers[{position}] repeats cik {cik}"
            )
        members[cik] = issuer
        if tier == "deep":
            deep_ciks.append(cik)
    core_ciks = list(members)
    core_cik_set = set(core_ciks)
    deep_cik_set = set(deep_ciks)

    orphan_cells = 0
    orphan_reasons: dict[str, int] = {
        REASON_ORPHAN_CIK: 0,
        REASON_ORPHAN_WINDOW: 0,
        REASON_ORPHAN_WINDOWLESS: 0,
        REASON_ORPHAN_DEEP_COMPONENT: 0,
    }
    status_normalised: dict[str, int] = {}
    cell_generation_counts: dict[str, int] = {}
    issuer_cell_states: dict[str, dict[str, int]] = {
        cik: {state: 0 for state in _CELL_STATE_KEYS} for cik in core_ciks
    }
    core_periods = thresholds.core_periods
    deep_periods = thresholds.deep_periods
    # A member's declared window: the deep periods for deep members (core
    # periods are a subset of them by load-time refusal), the core periods
    # for core-only members.
    member_windows: dict[str, frozenset[str]] = {
        cik: (
            frozenset(deep_periods) | frozenset(core_periods)
            if cik in deep_cik_set
            else frozenset(core_periods)
        )
        for cik in core_ciks
    }
    cells_list = cells if isinstance(cells, list) else []
    for cell in cells_list:
        status = cell.get("status")
        state = _STATUS_STATES[status]
        if status != state:
            status_normalised[status] = status_normalised.get(status, 0) + 1
        generation = cell.get("source_generation_id")
        if isinstance(generation, str) and generation:
            cell_generation_counts[generation] = (
                cell_generation_counts.get(generation, 0) + 1
            )
        cik = cell.get("cik")
        if cik not in core_cik_set:
            orphan_cells += 1
            orphan_reasons[REASON_ORPHAN_CIK] += 1
            continue
        period_id = cell.get("period_id")
        field_id = cell.get("field_id")
        if not _is_windowless_field_id(field_id):
            # Ruling V1-a r4 (R1): only the windowless families — packet,
            # journey and specialist — are exempt from the window test.  A
            # metric, package or statement cell carrying the wildcard period
            # is an orphan, and so is a windowed period outside the member's
            # declared windows (ruling V1-a r3, M5) — neither is ever
            # silently counted.
            if period_id == WILDCARD_PERIOD:
                orphan_cells += 1
                orphan_reasons[REASON_ORPHAN_WINDOWLESS] += 1
                continue
            if period_id not in member_windows[cik]:
                orphan_cells += 1
                orphan_reasons[REASON_ORPHAN_WINDOW] += 1
                continue
        if _is_deep_only_field_id(field_id) and cik not in deep_cik_set:
            # Ruling V1-a r4 (R2): a deep-only component (package,
            # statement, specialist, packet or journey, either accepted
            # package spelling) on a member that is not deep is an orphan.
            orphan_cells += 1
            orphan_reasons[REASON_ORPHAN_DEEP_COMPONENT] += 1
            continue
        issuer_cell_states[cik][state] += 1

    def metric_scope(cik: str, periods: tuple[str, ...]) -> dict[str, Any]:
        present = absent = not_applicable = withheld = 0
        stale = failed_extraction = incomparable = 0
        failed: list[str] = []
        withheld_fields: list[str] = []
        # Seat ruling BLOCKER-1: label counts over exactly these scope cells.
        labels = {key: 0 for key in _LABEL_COUNT_KEYS}
        policies: dict[str, dict[str, int]] = {"qualifier": {}, "derivation": {}}
        for period in periods:
            for metric_id in all_metrics:
                field_id = f"metric:{metric_id}"
                cell = index.get((cik, period, field_id))
                if cell is None:
                    state, reason = STATE_ABSENT, REASON_CELL_MISSING
                else:
                    state = _STATUS_STATES[cell["status"]]
                    reason = _absent_reason(cell) if state != STATE_PRESENT else ""
                if state == STATE_PRESENT:
                    present += 1
                    labelled = False
                    for label, policy_key in _PRESENT_LABELS:
                        if cell.get(label) is None:
                            continue
                        labelled = True
                        count_key = (
                            "present_qualified" if label == "qualifier" else "present_composed"
                        )
                        labels[count_key] += 1
                        policy = cell[policy_key]
                        policies[label][policy] = policies[label].get(policy, 0) + 1
                    if not labelled:
                        labels["present_strict"] += 1
                elif state == STATE_NOT_APPLICABLE:
                    not_applicable += 1
                    basis = cell.get("na_basis")
                    labels[_NA_BASIS_COUNT_KEYS[NA_BASIS_KERNEL if basis is None else basis]] += 1
                elif state == STATE_STALE:
                    stale += 1
                    failed.append(_field_label(period, field_id, reason))
                elif state == STATE_FAILED_EXTRACTION:
                    failed_extraction += 1
                    failed.append(_field_label(period, field_id, reason))
                elif state == STATE_INCOMPARABLE:
                    incomparable += 1
                    failed.append(_field_label(period, field_id, reason))
                elif metric_id in formula:
                    # A formula metric that is not present is withheld: it
                    # stays in the applicable denominator and is still
                    # reported under ``withheld``, but (ruling V1-a r2, F1)
                    # it is a failed field for the pass decision with
                    # reason ``formula_inputs_absent``.
                    withheld += 1
                    withheld_fields.append(_field_label(period, field_id, reason))
                    failed.append(
                        _field_label(period, field_id, REASON_FORMULA_INPUTS_ABSENT)
                    )
                else:
                    absent += 1
                    failed.append(_field_label(period, field_id, reason))
        applicable = (
            present + absent + withheld + stale + failed_extraction + incomparable
        )
        rate = (present / applicable) if applicable else None
        return {
            "present": present,
            "applicable": applicable,
            "not_applicable": not_applicable,
            "withheld": withheld,
            "stale": stale,
            "failed_extraction": failed_extraction,
            "incomparable": incomparable,
            "rate": rate,
            "failed": failed,
            "withheld_fields": withheld_fields,
            **labels,
            "qualifier_policies": policies["qualifier"],
            "derivation_policies": policies["derivation"],
        }

    def scope_unlabelled(scope: Mapping[str, Any]) -> bool:
        return not any(scope[key] for key in _NON_STRICT_COUNT_KEYS)

    deep = thresholds.tiers["deep"]
    deep_component_specs: list[tuple[str, str, bool]] = []
    for period in deep_periods:
        for role in deep["required_package_roles"]:
            deep_component_specs.append((period, f"package:{role}", False))
        for kind in deep["required_statements"]:
            deep_component_specs.append((period, f"statement:{kind}", False))
    for pack in deep["specialist_packs"]:
        deep_component_specs.append((WILDCARD_PERIOD, f"specialist:{pack}", True))
    if deep["require_packet"]:
        deep_component_specs.append((WILDCARD_PERIOD, "packet", False))
    if deep["require_journey"]:
        deep_component_specs.append((WILDCARD_PERIOD, "journey", False))

    def deep_components(
        cik: str,
    ) -> tuple[dict[str, dict[str, int]], list[str], int]:
        counts: dict[str, dict[str, int]] = {}
        failed: list[str] = []
        # Seat ruling BLOCKER-1: component cells carrying a present label or a
        # non-kernel N/A basis.
        labelled = 0
        for period, field_id, allows_not_applicable in deep_component_specs:
            bucket = counts.setdefault(
                field_id, {key: 0 for key in _COMPONENT_BUCKET_KEYS}
            )
            cell = index.get((cik, period, field_id))
            if cell is None:
                bucket["missing"] += 1
                failed.append(_field_label(period, field_id, REASON_CELL_MISSING))
                continue
            if (
                any(cell.get(label) is not None for label, _ in _PRESENT_LABELS)
                or cell.get("na_basis") not in (None, NA_BASIS_KERNEL)
            ):
                labelled += 1
            state = _STATUS_STATES[cell["status"]]
            bucket[state] += 1
            if state == STATE_PRESENT:
                continue
            if state == STATE_NOT_APPLICABLE and allows_not_applicable:
                continue
            failed.append(_field_label(period, field_id, _absent_reason(cell)))
        return counts, failed, labelled

    band_names = list(thresholds.band_names) + [NO_APPLICABLE_FIELDS_BAND]

    def empty_bands() -> dict[str, int]:
        return {name: 0 for name in band_names}

    issuer_entries: list[dict[str, Any]] = []
    proof_by_cik: dict[str, dict[str, Any]] = {}
    for cik in core_ciks:
        issuer = members[cik]
        is_deep = cik in deep_cik_set
        core_scope = metric_scope(cik, core_periods)
        # Ruling V1-a r2 (F1/F3): an issuer counts toward a tier only when
        # its band for that tier's scope is ``complete`` and its failed-field
        # list is empty; a ``no_applicable_fields`` band never passes.
        core_band = thresholds.band_for_rate(core_scope["rate"])
        core_pass = not core_scope["failed"] and core_band == COMPLETE_BAND
        # Seat ruling BLOCKER-1: complete with no labelled scope cell; ruling
        # V1A-S1 (fail-closed): only an issuer that passes the tier.
        core_strict = (
            core_pass
            and core_band == COMPLETE_BAND
            and scope_unlabelled(core_scope)
        )
        entry: dict[str, Any] = {
            "cik": cik,
            "ticker": issuer.get("ticker") if isinstance(issuer.get("ticker"), str) else "",
            "tier": issuer.get("tier_assigned"),
            "core_pass": core_pass,
        }
        if is_deep:
            deep_scope = metric_scope(cik, deep_periods)
            component_counts, component_failed, component_labelled = deep_components(cik)
            deep_labels = deep_scope["failed"] + component_failed
            deep_band = thresholds.band_for_rate(deep_scope["rate"])
            deep_pass = not deep_labels and deep_band == COMPLETE_BAND
            deep_strict = (
                deep_pass
                and deep_band == COMPLETE_BAND
                and scope_unlabelled(deep_scope)
                and component_labelled == 0
            )
            own = deep_scope
            own_strict = deep_strict
            entry["deep_pass"] = deep_pass
            entry["field_rate"] = own["rate"]
            entry["band"] = deep_band
            entry["failed_fields"] = sorted(
                set(deep_labels) | set(core_scope["failed"])
            )
            entry["withheld_fields"] = sorted(set(own["withheld_fields"]))
            proof_by_cik[cik] = {
                "core_scope": core_scope,
                "core_labels": core_scope["failed"],
                "deep_scope": deep_scope,
                "deep_labels": deep_labels,
                "components": component_counts,
                "core_pass": core_pass,
                "deep_pass": deep_pass,
                "core_strict": core_strict,
                "deep_strict": deep_strict,
                "component_labelled": component_labelled,
            }
        else:
            own = core_scope
            own_strict = core_strict
            entry["deep_pass"] = None
            entry["field_rate"] = core_scope["rate"]
            entry["band"] = core_band
            entry["failed_fields"] = sorted(core_scope["failed"])
            entry["withheld_fields"] = sorted(core_scope["withheld_fields"])
            proof_by_cik[cik] = {
                "core_scope": core_scope,
                "core_labels": core_scope["failed"],
                "deep_scope": None,
                "deep_labels": [],
                "components": {},
                "core_pass": core_pass,
                "deep_pass": None,
                "core_strict": core_strict,
                "deep_strict": None,
                "component_labelled": 0,
            }
        # Seat ruling BLOCKER-1: over the entry's own scope (the same scope
        # as its ``band``).
        entry["na_not_presented"] = own["na_not_presented"]
        entry["na_class"] = own["na_class"]
        entry["present_qualified"] = own["present_qualified"]
        entry["present_composed"] = own["present_composed"]
        entry["complete_strict"] = own_strict
        issuer_entries.append(entry)

    def tier_block(cik_list: list[str], target: int, *, use_deep: bool) -> dict[str, Any]:
        fields = {
            "present": 0,
            "applicable": 0,
            "not_applicable": 0,
            "withheld": 0,
            "stale": 0,
            "failed_extraction": 0,
            "incomparable": 0,
        }
        fields.update({key: 0 for key in _LABEL_COUNT_KEYS})
        bands = empty_bands()
        failing_reasons: dict[str, int] = {}
        components: dict[str, dict[str, int]] = {}
        policies: dict[str, dict[str, int]] = {
            "qualifier_policies": {},
            "derivation_policies": {},
        }
        complete_strict = 0
        component_labelled = 0
        pass_count = 0
        incomplete: list[str] = []
        for cik in cik_list:
            proof = proof_by_cik[cik]
            scope = proof["deep_scope"] if use_deep else proof["core_scope"]
            for key in fields:
                fields[key] += scope[key]
            bands[thresholds.band_for_rate(scope["rate"])] += 1
            if proof["deep_strict"] if use_deep else proof["core_strict"]:
                complete_strict += 1
            if use_deep:
                component_labelled += proof["component_labelled"]
            for policy_key, merged in policies.items():
                for policy, count in scope[policy_key].items():
                    merged[policy] = merged.get(policy, 0) + count
            tier_pass = proof["deep_pass"] if use_deep else proof["core_pass"]
            if tier_pass:
                pass_count += 1
            else:
                incomplete.append(cik)
            labels = proof["deep_labels"] if use_deep else proof["core_labels"]
            for label in labels:
                reason = _reason_of(label)
                failing_reasons[reason] = failing_reasons.get(reason, 0) + 1
            if use_deep:
                for field_id, bucket in proof["components"].items():
                    target_bucket = components.setdefault(
                        field_id, {key: 0 for key in _COMPONENT_BUCKET_KEYS}
                    )
                    for key in target_bucket:
                        target_bucket[key] += bucket[key]
        members_count = len(cik_list)
        if len(incomplete) != members_count - pass_count:
            raise AssertionError(
                "incomplete issuer list must equal members minus pass: "
                f"{len(incomplete)} != {members_count} - {pass_count}"
            )
        # Seat ruling BLOCKER-1 invariants: labels partition, never inflate.
        if fields["present_strict"] > fields["present"]:
            raise AssertionError(
                "present_strict must not exceed present: "
                f"{fields['present_strict']} > {fields['present']}"
            )
        na_total = fields["na_kernel"] + fields["na_not_presented"] + fields["na_class"]
        if na_total != fields["not_applicable"]:
            raise AssertionError(
                "N/A bases must sum to not_applicable: "
                f"{na_total} != {fields['not_applicable']}"
            )
        if complete_strict > bands[COMPLETE_BAND]:
            raise AssertionError(
                "complete_strict must not exceed the complete band: "
                f"{complete_strict} > {bands[COMPLETE_BAND]}"
            )
        # Seat ruling V1A-S1: strict-complete issuers are a subset of passes.
        if complete_strict > pass_count:
            raise AssertionError(
                "complete_strict must not exceed pass: "
                f"{complete_strict} > {pass_count}"
            )
        rate = (fields["present"] / fields["applicable"]) if fields["applicable"] else None
        block = {
            "target": target,
            "members": members_count,
            "pass": pass_count,
            "target_met": pass_count >= target and members_count >= target,
            "shortfall": max(0, target - pass_count),
            "fields": {
                "present": fields["present"],
                "applicable": fields["applicable"],
                "not_applicable": fields["not_applicable"],
                "withheld": fields["withheld"],
                "stale": fields["stale"],
                "failed_extraction": fields["failed_extraction"],
                "incomparable": fields["incomparable"],
                "rate": rate,
                **{key: fields[key] for key in _LABEL_COUNT_KEYS},
            },
            "bands": bands,
            "failing_reasons": dict(sorted(failing_reasons.items())),
            "complete_strict": complete_strict,
            "qualifier_policies": dict(sorted(policies["qualifier_policies"].items())),
            "derivation_policies": dict(sorted(policies["derivation_policies"].items())),
        }
        if use_deep:
            block["component_labelled"] = component_labelled
            block["components"] = {
                field_id: dict(sorted(bucket.items()))
                for field_id, bucket in sorted(components.items())
            }
        return block, sorted(incomplete)

    deep_block, deep_incomplete = tier_block(deep_ciks, thresholds.deep_target, use_deep=True)
    core_block, core_incomplete = tier_block(core_ciks, thresholds.core_target, use_deep=False)

    # The manifest's own rollup is never trusted; disagreements are reported.
    rollup_mismatch: list[dict[str, Any]] = []
    rollup_fields = ("present_cells", "absent_cells", "na_cells")
    for issuer in issuers:
        cik = issuer.get("cik")
        proof = proof_by_cik.get(cik)
        if proof is None:
            continue
        states = issuer_cell_states[cik]
        comparisons: list[tuple[str, Any, Any]] = [
            ("core_pass", issuer.get("core_pass"), proof["core_pass"]),
            ("present_cells", issuer.get("present_cells"), states[STATE_PRESENT]),
            ("absent_cells", issuer.get("absent_cells"), states[STATE_ABSENT]),
            ("na_cells", issuer.get("na_cells"), states[STATE_NOT_APPLICABLE]),
        ]
        if cik in deep_cik_set:
            comparisons.append(("deep_pass", issuer.get("deep_pass"), proof["deep_pass"]))
        for field, manifest_value, proof_value in comparisons:
            # Ruling V1-a r3 (M3): a missing or ill-typed rollup field is a
            # reported mismatch, never a skipped comparison.  The entry
            # records a null manifest value so no ill-typed literal rides on
            # the report; both kinds block through ``rollup_mismatch``.
            if field in ("core_pass", "deep_pass"):
                well_typed = isinstance(manifest_value, bool)
            else:
                well_typed = isinstance(manifest_value, int) and not isinstance(
                    manifest_value, bool
                )
            if not well_typed:
                rollup_mismatch.append(
                    {
                        "cik": cik,
                        "field": field,
                        "manifest_value": None,
                        "proof_value": proof_value,
                        "reason": "rollup_field_invalid",
                    }
                )
            elif manifest_value != proof_value:
                rollup_mismatch.append(
                    {
                        "cik": cik,
                        "field": field,
                        "manifest_value": manifest_value,
                        "proof_value": proof_value,
                        "reason": "rollup_value_mismatch",
                    }
                )
    rollup_mismatch.sort(key=lambda item: (item["cik"], item["field"]))

    issuer_reasons: dict[str, int] = {}
    for issuer in issuers:
        reason = issuer.get("exclusion_reason")
        if isinstance(reason, str) and reason:
            issuer_reasons[reason] = issuer_reasons.get(reason, 0) + 1
    header = manifest.get("header")
    header_exclusions: dict[str, Any] = {}
    if isinstance(header, Mapping):
        header_exclusions = {
            key: header[key] for key in sorted(header) if "exclusion" in str(key)
        }

    def verbatim(key: str) -> Any:
        return manifest.get(key)

    # Ruling V1-a r3 (M4) plus r4 (R3): the manifest's census identity is
    # byte-bound for a draft and declared — never proved — for anything
    # else.  For a draft the draft identity is the sha256 this function
    # computed from the manifest bytes.  For a non-draft it is the
    # manifest's declared top-level ``manifest_draft_sha256`` (64 lowercase
    # hex): bytes alone cannot show which draft an attestation covers, so
    # the basis marks every non-draft identity ``declared_unverified`` and
    # the report asks for the attestation that carries the proof.  A
    # non-draft without a well-formed declaration has no draft identity and
    # fails the prefix pin below.  The thresholds'
    # ``manifest_draft_sha256_prefix`` must prefix that identity and the
    # check always runs; a manifest that declares its own
    # ``manifest_draft_sha256_prefix`` must declare the thresholds' pin
    # exactly.  ``cutoff_at`` and ``source_generation_id`` are still
    # compared against the manifest's top-level fields; every disagreement
    # is an acceptance blocker instead of a refusal, and the proof still
    # runs and reports.
    thresholds_identity = dict(thresholds.census_identity)
    manifest_identity = {
        "source_generation_id": manifest.get("source_generation_id"),
        "cutoff_at": manifest.get("cutoff_at"),
        "manifest_draft_sha256_prefix": manifest.get("manifest_draft_sha256_prefix"),
    }
    declared_draft_sha256 = manifest.get("manifest_draft_sha256")
    if manifest.get("draft") is True:
        draft_identity = manifest_sha256
        draft_identity_basis = "manifest_bytes_sha256"
    else:
        # Ruling V1-a r4 (R3): a non-draft's identity is declared, never
        # proved — whatever it declares stays unverified until the
        # attestation is checked, and an absent or ill-typed declaration
        # leaves the identity null and fails the pin check below.
        draft_identity = (
            declared_draft_sha256
            if isinstance(declared_draft_sha256, str)
            and _SHA256_HEX.fullmatch(declared_draft_sha256)
            else None
        )
        draft_identity_basis = "declared_unverified"
    identity_mismatched_fields = [
        field
        for field in ("source_generation_id", "cutoff_at")
        if manifest_identity[field] != thresholds_identity[field]
    ]
    if not (
        isinstance(draft_identity, str)
        and draft_identity.startswith(
            thresholds_identity["manifest_draft_sha256_prefix"]
        )
    ):
        identity_mismatched_fields.append("manifest_draft_sha256_prefix")
    declared_prefix = manifest_identity["manifest_draft_sha256_prefix"]
    if (
        declared_prefix is not None
        and declared_prefix
        != thresholds_identity["manifest_draft_sha256_prefix"]
    ):
        # Ruling V1-a r4 (R3): a manifest-declared prefix that disagrees
        # with the thresholds' pin is its own mismatched field.
        identity_mismatched_fields.append("manifest_draft_sha256_prefix_declared")
    manifest_generation = manifest_identity["source_generation_id"]
    mixed_source_generations = any(
        generation != manifest_generation for generation in cell_generation_counts
    )
    census_identity_block = {
        "thresholds": thresholds_identity,
        "manifest": manifest_identity,
        "mismatched_fields": sorted(identity_mismatched_fields),
        "cell_source_generation_counts": dict(sorted(cell_generation_counts.items())),
        "mixed_source_generations": mixed_source_generations,
        "draft_identity": draft_identity,
        "draft_identity_basis": draft_identity_basis,
    }
    if draft_identity_basis == "declared_unverified":
        # Ruling V1-a r4 (R3): non-blocking — the declared identity needs
        # the attestation, and the report says so.
        census_identity_block["draft_identity_trust"] = "attestation_required"

    # Rulings V1-a r3 (M1/M2): ``freeze_ref`` is resolved inside the
    # repository root and only the declared relative path, its validity, its
    # existence and its bytes' sha256 enter the report — never an absolute
    # host path.
    freeze_ref_state = _freeze_ref_state(thresholds.freeze_ref)

    report_manifest = {
        "schema": verbatim("schema"),
        "sha256": manifest_sha256,
        "source_generation_id": verbatim("source_generation_id"),
        "cutoff_at": verbatim("cutoff_at"),
        "recorded_at": verbatim("recorded_at"),
        "draft": verbatim("draft"),
        "attested": verbatim("attested"),
        "basis": verbatim("basis"),
        # The attestation step's record of which draft this manifest attests
        # (ruling V1-a r3, M4); null on a draft or when undeclared.
        "manifest_draft_sha256": verbatim("manifest_draft_sha256"),
    }

    blockers: list[str] = []
    if report_manifest["draft"] is not False:
        blockers.append("manifest_draft")
    if report_manifest["attested"] is not True:
        blockers.append("manifest_unattested")
    if not deep_block["target_met"]:
        blockers.append("deep_target_not_met")
    if not core_block["target_met"]:
        blockers.append("core_target_not_met")
    if package_aliases_applied > 0:
        blockers.append(LEGACY_FIELD_ID_ALIAS_BLOCKER)
    if identity_mismatched_fields:
        blockers.append("census_identity_mismatch")
    if mixed_source_generations:
        blockers.append("mixed_source_generations")
    if not freeze_ref_state["valid"]:
        # Ruling V1-a r3 (M1): an absolute path, a traversal, a backslash,
        # an empty segment, an escape from the root, or a non-regular file.
        blockers.append("freeze_ref_invalid")
    elif not freeze_ref_state["exists"]:
        blockers.append("freeze_ref_missing")
    # Ruling V1-a r2 (F5): orphan cells and rollup mismatches block
    # acceptance; they were reported but non-blocking before.
    if orphan_cells > 0:
        blockers.append("orphan_cells")
    if rollup_mismatch:
        blockers.append("rollup_mismatch")
    blockers.sort()

    issuer_entries.sort(key=lambda entry: entry["cik"])
    return {
        "schema": PROOF_SCHEMA,
        "proved_at": utc_text(proved_at),
        "thresholds": {
            "thresholds_id": thresholds.thresholds_id,
            "content_sha256": thresholds.content_sha256,
            "deep_target": thresholds.deep_target,
            "core_target": thresholds.core_target,
            "freeze_ref": thresholds.freeze_ref,
            "freeze_ref_valid": freeze_ref_state["valid"],
            "freeze_ref_exists": freeze_ref_state["exists"],
            "freeze_ref_sha256": freeze_ref_state["sha256"],
        },
        "manifest": report_manifest,
        # The manifest bytes' sha256, computed by the prover itself from the
        # bytes it was handed (ruling V1-a r3, M4); the draft identity used
        # for the prefix pin rides in ``census_identity``.
        "manifest_sha256": manifest_sha256,
        "census_identity": census_identity_block,
        "tiers": {"core": core_block, "deep": deep_block},
        "issuers": issuer_entries,
        "incomplete_issuers": {"deep": deep_incomplete, "core": core_incomplete},
        "manifest_rollup_mismatch": rollup_mismatch,
        "exclusions": {
            "issuer_reasons": dict(sorted(issuer_reasons.items())),
            "header": header_exclusions,
        },
        "orphan_cells": orphan_cells,
        "orphan_reasons": dict(sorted(orphan_reasons.items())),
        "status_normalised": dict(sorted(status_normalised.items())),
        "field_id_aliases_applied": {
            LEGACY_PACKAGE_ALIAS_PREFIX: package_aliases_applied
        },
        "acceptance_eligible": not blockers,
        "acceptance_blockers": blockers,
    }


# ---------------------------------------------------------------------------
# Print block
# ---------------------------------------------------------------------------


def _labels_text(fields: Mapping[str, Any]) -> str:
    return " ".join(f"{key}={fields[key]}" for key in _LABEL_COUNT_KEYS)


def render_print(report: Mapping[str, Any]) -> str:
    """Render the fixed C2 census-parity print block from a proof report."""
    tiers = report["tiers"]
    manifest = report["manifest"]
    deep = tiers["deep"]
    core = tiers["core"]
    deep_fields = deep["fields"]
    core_fields = core["fields"]
    deep_bands = deep["bands"]
    core_bands = core["bands"]
    incomplete = report["incomplete_issuers"]
    issuer_reasons = report["exclusions"]["issuer_reasons"]
    exclusions_text = (
        " ".join(f"{reason}={count}" for reason, count in sorted(issuer_reasons.items()))
        or "none"
    )
    blockers = report["acceptance_blockers"]
    blockers_text = ",".join(blockers) if blockers else "none"
    eligible_text = "true" if report["acceptance_eligible"] else "false"
    lines = [
        f"C2 coverage  cutoff={manifest['cutoff_at']}  "
        f"source_generation={manifest['source_generation_id']}  "
        f"manifest={str(manifest['sha256'])[:20]}",
        f"deep issuers:   {deep['pass']} / {deep['target']:<4}  (members={deep['members']})",
        f"core issuers:   {core['pass']} / {core['target']:<4}  (members={core['members']})",
        f"deep fields:    {deep_fields['present']} / {deep_fields['applicable']}   "
        f"(deep members x A1,A2,I1,I2; N/A excluded; withheld={deep_fields['withheld']})",
        f"core fields:    {core_fields['present']} / {core_fields['applicable']}   "
        f"(core members x A1,I1; N/A excluded; withheld={core_fields['withheld']})",
        f"deep bands:     complete={deep_bands['complete']} "
        f"complete_strict={deep['complete_strict']} high={deep_bands['high']} "
        f"partial={deep_bands['partial']} low={deep_bands['low']} "
        f"no_applicable_fields={deep_bands['no_applicable_fields']}",
        f"core bands:     complete={core_bands['complete']} "
        f"complete_strict={core['complete_strict']} high={core_bands['high']} "
        f"partial={core_bands['partial']} low={core_bands['low']} "
        f"no_applicable_fields={core_bands['no_applicable_fields']}",
        "deep labels:    " + _labels_text(deep_fields),
        "core labels:    " + _labels_text(core_fields),
        f"incomplete:     deep={len(incomplete['deep'])} core={len(incomplete['core'])}   "
        f"(every one listed in the report)",
        f"exclusions:     {exclusions_text}",
        f"acceptance:     eligible={eligible_text}  blockers={blockers_text}",
    ]
    return "\n".join(lines) + "\n"
