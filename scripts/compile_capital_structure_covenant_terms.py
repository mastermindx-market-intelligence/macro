"""Compile filing-text covenant clause observations into an immutable ledger.

Packet B-F09-5, source-first slice. The compiler is deliberately scoped to
retained SEC credit-agreement exhibits (EX-10.1..EX-10.5): it reads
manifest-addressed retained bytes through the existing capital_structure
source-identity/source-store/source-ledger seams, then transcribes only
explicit, closed-enum covenant clause values stated in the filing text. It
performs NO headroom/capacity computation, builds no instrument, and creates
no second store.

The compiler never fetches SEC HTTP endpoints. It may read already-retained
content-addressed source objects from the configured R2/local source store.

Usage:
    python -m scripts.compile_capital_structure_covenant_terms
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path
import tempfile
from typing import Any

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.capital_structure.covenant_terms import (  # noqa: E402
    COVENANT_EXHIBIT_TYPES,
    COVENANT_TERM_SCHEMA,
    CovenantSpanUnbound,
    compile_observations,
)
from engine.capital_structure.source_identity import (  # noqa: E402
    validate_manifest_content_binding,
    validate_manifest_ledger,
)
from engine.capital_structure.source_ledger_io import (  # noqa: E402
    read_source_ledger,
    source_ledger_path,
)
from engine.capital_structure.source_store import build_source_stores  # noqa: E402

COVENANT_OBSERVATION_COLUMNS = [
    "observation_id", "logical_observation_id", "issuer_id", "accession", "form",
    "source_manifest_id", "term_name", "clause_id", "state", "available_at",
    "correction_version", "observation_json",
]

# Round-5 review MAJOR fix: a row that fails the CURRENT contract is never
# deleted. It is retained verbatim (its exact canonical bytes) in this
# sidecar ledger, re-loaded and re-validated on every subsequent run
# alongside the main ledger, so a later contract fix can recover it and no
# run's _atomic_write of the main ledger can make it unrecoverable.
QUARANTINE_COLUMNS = ["observation_id", "logical_observation_id", "reason", "observation_json"]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _data_root() -> Path:
    from lib import config

    return config.data_dir() / "capital_structure"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _native(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native(item) for item in value]
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
        try:
            converted = value.tolist()
            if converted is not value:
                return _native(converted)
        except Exception:  # noqa: BLE001
            pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            pass
    return value


def _load_contract(name: str) -> dict[str, Any]:
    return json.loads((_repo_root() / "contracts" / name).read_text(encoding="utf-8"))


def _validate_schema(record: Mapping[str, Any], schema: Mapping[str, Any], label: str) -> None:
    from jsonschema import Draft202012Validator, FormatChecker

    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record))
    if errors:
        joined = "; ".join(
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:5]
        )
        raise ValueError(f"{label} contract violation: {joined}")


def _selected_covenant_manifests(manifests: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = []
    for manifest in manifests:
        document = manifest.get("document") or {}
        if (
            str(manifest.get("source_system") or "") == "sec_edgar"
            and str(document.get("document_role") or "") == "exhibit"
            and str(document.get("document_type") or "") in COVENANT_EXHIBIT_TYPES
        ):
            selected.append(dict(manifest))
    selected.sort(key=lambda row: str(row.get("manifest_id") or ""))
    return selected


def _load_parquet_json_rows(
    path: Path, columns: Sequence[str], label: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Read a parquet ledger of ``{..., "observation_json": <canonical json>}``
    rows and return ``(raw_json, observation)`` pairs. Malformed on-disk
    bytes (bad columns, non-JSON, non-canonical encoding) are always a hard
    failure -- that is disk corruption, not schema drift."""
    if not path.exists():
        return []
    frame = pd.read_parquet(path)
    if frame.columns.tolist() != list(columns):
        raise ValueError(f"{label} columns must exactly equal {list(columns)}; got {frame.columns.tolist()}")
    rows: list[tuple[str, dict[str, Any]]] = []
    for index, row in frame.iterrows():
        raw = row["observation_json"]
        if not isinstance(raw, str) or not raw:
            raise ValueError(f"{label} row {index} lacks canonical observation_json")
        try:
            observation = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} row {index} has malformed observation_json") from exc
        if not isinstance(observation, Mapping):
            raise ValueError(f"{label} row {index} observation_json must be an object")
        rows.append((raw, dict(observation)))
    return rows


def _load_existing_observations(
    ledger_path: Path, quarantine_path: Path, schema: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(observations, quarantined)``.

    Ruling Minor-2 (round-4) + round-5 review MAJOR fix: a historical row
    that fails validation against the CURRENT contract is quarantined --
    excluded from the compiled/valid set and reported with a reason --
    rather than raising and failing the entire compile. The contract is
    expected to evolve (this very PR changed ``evidence.publication``'s
    shape, the relationships/version id patterns, and added a required
    ``period_start``); a schema edit must never turn every future nightly
    run into a hard outage over ledger rows written under a prior shape.

    Unlike the round-4 shape, a quarantined row is never permanently
    deleted: it is retained verbatim (its exact canonical bytes) in the
    sidecar ``quarantine_path`` ledger, so it is re-loaded and re-validated
    here on every subsequent run alongside the main ledger -- a later
    contract fix can recover it, and no run's ``_atomic_write`` of the main
    ledger (an unconditional full-file rewrite) can make a quarantined row
    unrecoverable. Malformed on-disk bytes in either file remain a hard
    failure -- that is disk corruption, not schema drift, and is never
    silently dropped.
    """
    combined: list[tuple[str, dict[str, Any]]] = []
    combined.extend(_load_parquet_json_rows(ledger_path, COVENANT_OBSERVATION_COLUMNS, "covenant-term ledger"))
    combined.extend(_load_parquet_json_rows(quarantine_path, QUARANTINE_COLUMNS, "covenant-term quarantine"))

    observations: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []
    for raw, observation in combined:
        try:
            _validate_schema(observation, schema, "covenant-term ledger row")
        except ValueError as exc:
            quarantined.append({
                "observation_id": observation.get("observation_id"),
                "logical_observation_id": observation.get("logical_observation_id"),
                "reason": str(exc),
                "observation_json": raw,
            })
            continue
        if raw != _canonical_json(observation):
            raise ValueError("covenant-term ledger row observation_json is not canonical")
        observations.append(observation)
    return observations, quarantined


def _find_orphaned_lineage(
    observations: Sequence[Mapping[str, Any]], quarantined: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Round-5 review MAJOR fix: report (never silently write) a correction
    or supersession whose referenced PARENT observation is not present in
    the valid/compiled set -- e.g. because that parent was just quarantined
    (excluded from the current contract) while the child still validates and
    would otherwise be re-persisted pointing at an id nothing else names."""
    valid_ids = {str(obs.get("observation_id")) for obs in observations}
    quarantined_ids = {str(row.get("observation_id")) for row in quarantined}
    orphaned: list[dict[str, Any]] = []
    for obs in observations:
        version = obs.get("version") or {}
        correction_of = version.get("correction_of")
        if correction_of and str(correction_of) not in valid_ids:
            orphaned.append({
                "observation_id": obs.get("observation_id"),
                "relation": "version.correction_of",
                "missing_parent_id": correction_of,
                "parent_quarantined": str(correction_of) in quarantined_ids,
            })
        relationships = obs.get("relationships") or {}
        for parent_id in relationships.get("supersedes") or []:
            if str(parent_id) not in valid_ids:
                orphaned.append({
                    "observation_id": obs.get("observation_id"),
                    "relation": "relationships.supersedes",
                    "missing_parent_id": parent_id,
                    "parent_quarantined": str(parent_id) in quarantined_ids,
                })
    return orphaned


def _to_quarantine_frame(quarantined: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows = [
        {
            "observation_id": row.get("observation_id"),
            "logical_observation_id": row.get("logical_observation_id"),
            "reason": row.get("reason"),
            "observation_json": row["observation_json"],
        }
        for row in quarantined
    ]
    return pd.DataFrame(rows, columns=QUARANTINE_COLUMNS)


def _validate_observation_lineage(
    observations: Sequence[Mapping[str, Any]], manifests: Sequence[Mapping[str, Any]],
    schema: Mapping[str, Any],
) -> None:
    by_manifest = {str(row["manifest_id"]): row for row in manifests}
    for index, raw in enumerate(observations):
        observation = dict(raw)
        _validate_schema(observation, schema, f"output covenant-term {index}")
        document = observation.get("document") or {}
        evidence = observation.get("evidence") or {}
        manifest_id = str(document.get("source_manifest_id") or "")
        manifest = by_manifest.get(manifest_id)
        if manifest is None:
            raise ValueError(f"output covenant-term {index} source manifest is absent from the ledger")
        source_document = manifest.get("document") or {}
        if (
            str(evidence.get("source_manifest_id") or "") != manifest_id
            or str(evidence.get("source_document_sha256") or "").lower()
            != str(source_document.get("content_sha256") or "").lower()
            or str(document.get("content_sha256") or "").lower()
            != str(source_document.get("content_sha256") or "").lower()
        ):
            raise ValueError(f"output covenant-term {index} has detached source evidence")
        if str(source_document.get("document_role") or "") != "exhibit":
            raise ValueError(f"output covenant-term {index} source is not a retained exhibit")


def _to_frame(observations: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for observation in observations:
        filing = observation.get("filing") or {}
        document = observation.get("document") or {}
        term = observation.get("term") or {}
        clause = observation.get("clause") or {}
        state = observation.get("state") or {}
        point_in_time = observation.get("point_in_time") or {}
        version = observation.get("version") or {}
        rows.append({
            "observation_id": observation["observation_id"],
            "logical_observation_id": observation["logical_observation_id"],
            "issuer_id": observation["issuer_id"],
            "accession": filing["accession"], "form": filing["form"],
            "source_manifest_id": document["source_manifest_id"],
            "term_name": term["name"], "clause_id": clause.get("clause_id"),
            "state": state["disposition"],
            "available_at": point_in_time["available_at"],
            "correction_version": int(version["correction_version"]),
            "observation_json": _canonical_json(observation),
        })
    return pd.DataFrame(rows, columns=COVENANT_OBSERVATION_COLUMNS)


def _atomic_write(frame: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp.parquet", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        frame.to_parquet(temporary, index=False)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def _source_reader_for_store(source_store):
    if isinstance(source_store, Mapping):
        stores = dict(source_store)
    elif source_store is None:
        stores = {}
    else:
        stores = {str(source_store.store_id): source_store}

    def read(manifest: Mapping[str, Any]) -> bytes | None:
        storage = manifest.get("storage") or {}
        document = manifest.get("document") or {}
        store = stores.get(str(storage.get("store_id") or ""))
        if store is None:
            return None
        return store.get_verified(
            str(storage.get("object_key") or ""),
            str(document.get("content_sha256") or "").lower(),
        )
    return read


def compile_from_disk(
    root: Path | None = None, *, generated_at: str | None = None, source_store=None,
) -> dict[str, Any]:
    """Compile append-only covenant clause observations without SEC fetches.

    Source bytes are obtained only through the manifest-addressed local/R2
    store, where an R2 read is an integrity-checked evidence retrieval rather
    than a new SEC acquisition.
    """
    root = root or _data_root()
    manifest_path = source_ledger_path(root)
    ledger_path = root / "covenant_term_observations.parquet"
    quarantine_path = root / "covenant_term_observations.quarantined.parquet"
    manifest_schema = _load_contract("capital_structure_source_manifest.schema.json")
    observation_schema = _load_contract("capital_structure_covenant_term_observation.schema.json")
    all_manifests = read_source_ledger(manifest_path)
    for index, manifest in enumerate(all_manifests):
        _validate_schema(manifest, manifest_schema, f"source manifest {index}")
        validate_manifest_content_binding(manifest)
    validate_manifest_ledger(all_manifests)

    manifests = _selected_covenant_manifests(all_manifests)
    existing, quarantined = _load_existing_observations(ledger_path, quarantine_path, observation_schema)
    existing_by_logical: dict[str, list[dict[str, Any]]] = {}
    for obs in existing:
        existing_by_logical.setdefault(str(obs.get("logical_observation_id")), []).append(obs)

    store = source_store if source_store is not None else build_source_stores()
    reader = _source_reader_for_store(store)

    generated = generated_at or _now_iso()
    observations: list[dict[str, Any]] = list(existing)
    deferred = 0
    for manifest in manifests:
        content = reader(manifest)
        if content is None:
            deferred += 1
            continue
        text = content.decode("utf-8", errors="replace")
        prior_for_manifest = [
            obs for group in existing_by_logical.values() for obs in group
            if (obs.get("document") or {}).get("source_manifest_id") == manifest.get("manifest_id")
        ]
        try:
            new_observations = compile_observations(
                manifest, text, generated_at=generated, prior_observations=prior_for_manifest,
            )
        except CovenantSpanUnbound:
            deferred += 1
            continue
        existing_ids = {obs["observation_id"] for obs in observations}
        for obs in new_observations:
            if obs["observation_id"] not in existing_ids:
                observations.append(obs)

    _validate_observation_lineage(observations, all_manifests, observation_schema)
    # Round-5 review MAJOR fix: a correction/supersession whose PARENT is not
    # in the valid set (typically because that parent was just quarantined)
    # is reported here, never silently re-persisted with a dangling pointer.
    orphaned_lineage = _find_orphaned_lineage(observations, quarantined)
    _atomic_write(_to_frame(observations), ledger_path)
    # Round-5 review MAJOR fix: the quarantine sidecar is written every run
    # (even when empty, mirroring the main ledger) so it always reflects the
    # CURRENT quarantine state -- a row that heals under a later contract
    # fix disappears from here because it is re-loaded into `observations`
    # above, never because this file silently dropped it.
    _atomic_write(_to_quarantine_frame(quarantined), quarantine_path)
    return {
        "status": "ok",
        "schema": COVENANT_TERM_SCHEMA,
        "eligible_manifests": len(manifests),
        "deferred": deferred,
        "observations": len(observations),
        # Ruling Minor-2: rows quarantined this run (excluded from the
        # compiled/valid set because they fail the CURRENT contract) are
        # counted and listed with reasons, never silently dropped and never
        # fatal. Round-5 review MAJOR fix: they are also retained verbatim
        # on disk in `quarantine_path`, not deleted -- see
        # `_load_existing_observations`.
        "quarantined": len(quarantined),
        "quarantined_rows": [
            {
                "observation_id": row.get("observation_id"),
                "logical_observation_id": row.get("logical_observation_id"),
                "reason": row.get("reason"),
            }
            for row in quarantined
        ],
        # Round-5 review MAJOR fix: never silent -- a correction/supersession
        # pointing at an id absent from the valid set is named here.
        "orphaned_lineage": orphaned_lineage,
        "path": str(ledger_path),
        "quarantine_path": str(quarantine_path),
    }


def _write_failure_marker(root: Path, reason: str) -> Path:
    from engine.capital_structure.ingestion_health import COVENANT_EXTRACTION_FAILURE_FILENAME

    path = root / COVENANT_EXTRACTION_FAILURE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"state": "failed", "reason": reason[:500], "failed_at": _now_iso()}
    tmp = path.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path


def _clear_failure_marker(root: Path) -> None:
    from engine.capital_structure.ingestion_health import COVENANT_EXTRACTION_FAILURE_FILENAME

    path = root / COVENANT_EXTRACTION_FAILURE_FILENAME
    if path.exists():
        path.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    """Never propagates an exception with a non-zero exit. This step runs
    immediately before daily.yml's fail-closed health gate (`check
    capital-structure ingestion health`); the gate itself must independently
    decide pass/fail from the health artifact, not from this step's exit code
    (F13 alarm-bus law: a producer bug may never fail that OTHER gate). Any
    exception here is recorded as a typed `covenant_extraction: {state:
    failed, reason}` marker that evaluate_health() reads on the very next
    step, and this process still exits 0."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    # Everything that can raise -- including resolving the data root itself --
    # stays inside this one try block. Round-3 review Major 3: `root =
    # _data_root()` used to sit OUTSIDE the try, so a config/import failure
    # there (or anywhere else in this function) would propagate past this
    # wrapper and kill the daily.yml step before the fail-closed health gate
    # ever ran -- exactly the F13 outcome BLOCKER-1 required this wrapper to
    # prevent. `root` defaults to the repo-relative data dir so the failure
    # marker still has somewhere to land even if `_data_root()` itself failed.
    root = _repo_root() / "data" / "capital_structure"
    try:
        root = _data_root()
        result = compile_from_disk(root)
        # Minor-1 (round-4 review): this call used to sit OUTSIDE the try
        # block, so an OSError/PermissionError from path.unlink() on an
        # otherwise-successful run would still propagate straight out of
        # main() -- the exact "never propagates an exception" contract this
        # docstring promises. It now shares the same catch-all below.
        _clear_failure_marker(root)
    except Exception as exc:  # noqa: BLE001 -- deliberate catch-all, see docstring
        reason = f"{type(exc).__name__}: {exc}"
        try:
            marker_path: Path | None = _write_failure_marker(root, reason)
        except Exception as marker_exc:  # noqa: BLE001 -- marker write must never re-raise
            marker_path = None
            reason = f"{reason} (failure marker write also failed: {marker_exc})"
        print(json.dumps({
            "status": "failed",
            "schema": COVENANT_TERM_SCHEMA,
            "reason": reason[:500],
            "marker": str(marker_path) if marker_path is not None else None,
        }, sort_keys=True))
        return 0
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
