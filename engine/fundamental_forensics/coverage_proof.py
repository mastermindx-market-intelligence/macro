"""C2 coverage proof: predeclared thresholds proven from a coverage manifest.

Acceptance case A36 — "predeclare issuer/period/field thresholds; prove them
by manifest, not ticker loop count."  This module is pure: no network, no
store, no wall-clock read, and no import from ``scripts/``.  It reads a frozen
thresholds config, the governed metric catalog, and a
``fundamental_forensics.coverage_manifest/v1`` document, and produces a
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
REASON_CELL_MISSING = "cell_missing"
NO_APPLICABLE_FIELDS_BAND = "no_applicable_fields"

_CIK = re.compile(r"^[0-9]{10}$")
_METRIC_FIELD = re.compile(r"^metric:\S+$")
_PACKAGE_FIELD = re.compile(r"^package:\S+$")
_STATEMENT_FIELD = re.compile(r"^statement:\S+$")
_SPECIALIST_FIELD = re.compile(r"^specialist:PK[0-9]{2}$")
_BARE_FIELDS = frozenset({"packet", "journey"})

# Manifest status -> proof state.  ``slot_absent`` is never turned into
# ``not_applicable``; only an explicit ``not_applicable`` leaves the
# applicable denominator.
_STATUS_STATES: Mapping[str, str] = {
    "present": STATE_PRESENT,
    "not_applicable": STATE_NOT_APPLICABLE,
    "absent": STATE_ABSENT,
    "slot_absent": STATE_ABSENT,
}

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


def _check_cell_shape(cell: Any, position: int) -> tuple[str, str, str]:
    """Validate one cell; return ``(cik, period_id, field_id)``."""
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
    if not isinstance(field_id, str) or not (
        _METRIC_FIELD.fullmatch(field_id)
        or _PACKAGE_FIELD.fullmatch(field_id)
        or _STATEMENT_FIELD.fullmatch(field_id)
        or _SPECIALIST_FIELD.fullmatch(field_id)
        or field_id in _BARE_FIELDS
    ):
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
    source_generation_id = cell.get("source_generation_id")
    if not isinstance(source_generation_id, str) or not source_generation_id:
        raise shape(
            "source_generation_id must be a non-empty string; no coverage row "
            "without it"
        )
    return cik, period_id, field_id


def _index_cells(cells: Any) -> dict[tuple[str, str, str], Mapping[str, Any]]:
    if not isinstance(cells, list):
        raise CoverageProofError("manifest_limits", "manifest cells must be a list")
    if len(cells) > HARD_MAX_CELLS:
        raise CoverageProofError(
            "manifest_limits",
            f"manifest carries {len(cells)} cells; the hard limit is {HARD_MAX_CELLS}",
        )
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for position, cell in enumerate(cells):
        key = _check_cell_shape(cell, position)
        if key in index:
            raise CoverageProofError(
                "duplicate_cell",
                f"cells[{position}] repeats (cik, period_id, field_id)={key}",
            )
        index[key] = cell
    return index


def _validate_manifest_document(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise CoverageProofError(
            "manifest_schema", "manifest must be a JSON object"
        )
    schema = manifest.get("schema")
    if schema != MANIFEST_SCHEMA:
        raise CoverageProofError(
            "manifest_schema",
            f"manifest schema must equal {MANIFEST_SCHEMA}; got {schema!r}",
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
    _index_cells(manifest.get("cells"))
    return manifest


def load_manifest(path: str | Path) -> tuple[dict[str, Any], str]:
    """Read a coverage manifest and return it with its raw-byte sha256."""
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
    data = Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    try:
        raw = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CoverageProofError(
            "manifest_undecodable", f"manifest is not decodable JSON: {exc}"
        ) from exc
    return _validate_manifest_document(raw), digest


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
    manifest: Any,
    manifest_sha256: str,
    thresholds: CoverageThresholds,
    direct_ids: Any,
    formula_ids: Any,
    *,
    proved_at: datetime,
) -> dict[str, Any]:
    """Recompute tier coverage from membership and required cells."""
    if not isinstance(proved_at, datetime):
        raise CoverageProofError("naive_clock", "proved_at must be a datetime")
    if proved_at.tzinfo is None or proved_at.utcoffset() is None:
        raise CoverageProofError(
            "naive_clock", "proved_at must carry an explicit timezone"
        )
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
    index = _index_cells(cells)

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
    status_normalised: dict[str, int] = {}
    issuer_cell_states: dict[str, dict[str, int]] = {
        cik: {STATE_PRESENT: 0, STATE_ABSENT: 0, STATE_NOT_APPLICABLE: 0}
        for cik in core_ciks
    }
    cells_list = cells if isinstance(cells, list) else []
    for cell in cells_list:
        status = cell.get("status")
        state = _STATUS_STATES[status]
        if status != state:
            status_normalised[status] = status_normalised.get(status, 0) + 1
        cik = cell.get("cik")
        if cik not in core_cik_set:
            orphan_cells += 1
            continue
        issuer_cell_states[cik][state] += 1

    core_periods = thresholds.core_periods
    deep_periods = thresholds.deep_periods

    def metric_scope(cik: str, periods: tuple[str, ...]) -> dict[str, Any]:
        present = absent = not_applicable = withheld = 0
        failed: list[str] = []
        withheld_fields: list[str] = []
        for period in periods:
            for metric_id in all_metrics:
                field_id = f"metric:{metric_id}"
                cell = index.get((cik, period, field_id))
                if cell is None:
                    state, reason = STATE_ABSENT, REASON_CELL_MISSING
                else:
                    state = _STATUS_STATES[cell["status"]]
                    reason = _absent_reason(cell) if state == STATE_ABSENT else ""
                if state == STATE_PRESENT:
                    present += 1
                elif state == STATE_NOT_APPLICABLE:
                    not_applicable += 1
                elif metric_id in formula:
                    # A formula metric absent is withheld: it does not fail the
                    # issuer and does not count as present, but stays in the
                    # applicable denominator.
                    withheld += 1
                    withheld_fields.append(_field_label(period, field_id, reason))
                else:
                    absent += 1
                    failed.append(_field_label(period, field_id, reason))
        applicable = present + absent + withheld
        rate = (present / applicable) if applicable else None
        return {
            "present": present,
            "applicable": applicable,
            "not_applicable": not_applicable,
            "withheld": withheld,
            "rate": rate,
            "failed": failed,
            "withheld_fields": withheld_fields,
        }

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

    def deep_components(cik: str) -> tuple[dict[str, dict[str, int]], list[str]]:
        counts: dict[str, dict[str, int]] = {}
        failed: list[str] = []
        for period, field_id, allows_not_applicable in deep_component_specs:
            bucket = counts.setdefault(
                field_id,
                {"present": 0, "absent": 0, "not_applicable": 0, "missing": 0},
            )
            cell = index.get((cik, period, field_id))
            if cell is None:
                bucket["missing"] += 1
                failed.append(_field_label(period, field_id, REASON_CELL_MISSING))
                continue
            state = _STATUS_STATES[cell["status"]]
            bucket[state] += 1
            if state == STATE_PRESENT:
                continue
            if state == STATE_NOT_APPLICABLE and allows_not_applicable:
                continue
            failed.append(_field_label(period, field_id, _absent_reason(cell)))
        return counts, failed

    band_names = list(thresholds.band_names) + [NO_APPLICABLE_FIELDS_BAND]

    def empty_bands() -> dict[str, int]:
        return {name: 0 for name in band_names}

    issuer_entries: list[dict[str, Any]] = []
    proof_by_cik: dict[str, dict[str, Any]] = {}
    for cik in core_ciks:
        issuer = members[cik]
        is_deep = cik in deep_cik_set
        core_scope = metric_scope(cik, core_periods)
        core_pass = not core_scope["failed"]
        entry: dict[str, Any] = {
            "cik": cik,
            "ticker": issuer.get("ticker") if isinstance(issuer.get("ticker"), str) else "",
            "tier": issuer.get("tier_assigned"),
            "core_pass": core_pass,
        }
        if is_deep:
            deep_scope = metric_scope(cik, deep_periods)
            component_counts, component_failed = deep_components(cik)
            deep_labels = deep_scope["failed"] + component_failed
            deep_pass = not deep_labels
            own = deep_scope
            entry["deep_pass"] = deep_pass
            entry["field_rate"] = own["rate"]
            entry["band"] = thresholds.band_for_rate(own["rate"])
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
            }
        else:
            entry["deep_pass"] = None
            entry["field_rate"] = core_scope["rate"]
            entry["band"] = thresholds.band_for_rate(core_scope["rate"])
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
            }
        issuer_entries.append(entry)

    def tier_block(cik_list: list[str], target: int, *, use_deep: bool) -> dict[str, Any]:
        fields = {"present": 0, "applicable": 0, "not_applicable": 0, "withheld": 0}
        bands = empty_bands()
        failing_reasons: dict[str, int] = {}
        components: dict[str, dict[str, int]] = {}
        pass_count = 0
        incomplete: list[str] = []
        for cik in cik_list:
            proof = proof_by_cik[cik]
            scope = proof["deep_scope"] if use_deep else proof["core_scope"]
            for key in fields:
                fields[key] += scope[key]
            bands[thresholds.band_for_rate(scope["rate"])] += 1
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
                        field_id,
                        {"present": 0, "absent": 0, "not_applicable": 0, "missing": 0},
                    )
                    for key in target_bucket:
                        target_bucket[key] += bucket[key]
        members_count = len(cik_list)
        if len(incomplete) != members_count - pass_count:
            raise AssertionError(
                "incomplete issuer list must equal members minus pass: "
                f"{len(incomplete)} != {members_count} - {pass_count}"
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
                "rate": rate,
            },
            "bands": bands,
            "failing_reasons": dict(sorted(failing_reasons.items())),
        }
        if use_deep:
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
            if field in ("core_pass", "deep_pass"):
                if not isinstance(manifest_value, bool):
                    continue
            elif not isinstance(manifest_value, int) or isinstance(manifest_value, bool):
                continue
            if manifest_value != proof_value:
                rollup_mismatch.append(
                    {
                        "cik": cik,
                        "field": field,
                        "manifest_value": manifest_value,
                        "proof_value": proof_value,
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

    report_manifest = {
        "schema": verbatim("schema"),
        "sha256": manifest_sha256,
        "source_generation_id": verbatim("source_generation_id"),
        "cutoff_at": verbatim("cutoff_at"),
        "recorded_at": verbatim("recorded_at"),
        "draft": verbatim("draft"),
        "attested": verbatim("attested"),
        "basis": verbatim("basis"),
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
        },
        "manifest": report_manifest,
        "tiers": {"core": core_block, "deep": deep_block},
        "issuers": issuer_entries,
        "incomplete_issuers": {"deep": deep_incomplete, "core": core_incomplete},
        "manifest_rollup_mismatch": rollup_mismatch,
        "exclusions": {
            "issuer_reasons": dict(sorted(issuer_reasons.items())),
            "header": header_exclusions,
        },
        "orphan_cells": orphan_cells,
        "status_normalised": dict(sorted(status_normalised.items())),
        "acceptance_eligible": not blockers,
        "acceptance_blockers": blockers,
    }


# ---------------------------------------------------------------------------
# Print block
# ---------------------------------------------------------------------------


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
        f"deep bands:     complete={deep_bands['complete']} high={deep_bands['high']} "
        f"partial={deep_bands['partial']} low={deep_bands['low']} "
        f"no_applicable_fields={deep_bands['no_applicable_fields']}",
        f"core bands:     complete={core_bands['complete']} high={core_bands['high']} "
        f"partial={core_bands['partial']} low={core_bands['low']} "
        f"no_applicable_fields={core_bands['no_applicable_fields']}",
        f"incomplete:     deep={len(incomplete['deep'])} core={len(incomplete['core'])}   "
        f"(every one listed in the report)",
        f"exclusions:     {exclusions_text}",
        f"acceptance:     eligible={eligible_text}  blockers={blockers_text}",
    ]
    return "\n".join(lines) + "\n"
