"""Selection-clock qualified owner reads composed from incumbent GMI owners."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from engine.theme_graph import identity_resolution as ir
from engine.theme_graph import rights
from engine.theme_graph import store
from engine.theme_graph import theme_state
from engine.theme_graph.identity import company_node_id, local_theme_node_id
from engine.theme_graph.ontology import (
    RepositoryStore,
    _collapse_relevant_edges,
    _nodes_as_known,
    _parse_date,
    _records,
)
from engine.theme_graph.selection_cohort import content_sha256

IDENTITY_OWNER_SCHEMA = "gmi.identity_resolution/v1"
MEMBERSHIP_OWNER_SCHEMA = "gmi.theme_graph_membership_pit/v1"
STATE_ARTIFACT_NAME = "shadow_theme_state.v1.json"

_REASON_STALE = "STALE_FOR_KNOWN_CLOCK"
_REASON_NO_OVERLAP = "NO_OVERLAP_AT_CLOCK"
_REASON_OWNER = "OWNER_UNAVAILABLE"

_MARKET_SUITE = {
    "us_today": "baskets",
    "cn_today": "baskets_china_ths",
    "complete-finalized-fixture": "baskets",
}


def _repo_data_dir(data_dir: Path | None) -> Path:
    if data_dir is not None:
        return Path(data_dir)
    from lib import config

    return config.data_dir()


def _rights_receipt_ref(path: Path | None) -> str:
    registry = path if path is not None else rights.registry_path()
    digest = hashlib.sha256(registry.read_bytes()).hexdigest()[:32]
    return f"config/theme_sources.yml@rights_{digest}"


def _clock_pair(selection: Mapping) -> tuple[str, str]:
    effective = selection["effective_at"]
    known = selection["known_at"]
    if not isinstance(effective, str) or not isinstance(known, str):
        raise ValueError("selection clocks must be precise owner timestamps")
    return effective, known


def _asof_date(effective_at: str) -> str:
    if "T" in effective_at:
        return dt.datetime.fromisoformat(effective_at.replace("Z", "+00:00")).date().isoformat()
    return effective_at[:10]


def _precise_timestamp(value: str, *, end_of_day: bool = False) -> str:
    if "T" in value:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    day = dt.date.fromisoformat(value[:10])
    if end_of_day:
        parsed = dt.datetime.combine(day, dt.time(23, 59, 59), tzinfo=dt.timezone.utc)
    else:
        parsed = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc)
    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _suite_for_selection(selection: Mapping) -> str:
    scope = str(selection.get("cohort_scope") or "")
    if scope in _MARKET_SUITE:
        return _MARKET_SUITE[scope]
    if scope.endswith("_today"):
        return _MARKET_SUITE.get(scope, "baskets")
    return "baskets"


def _company_node_from_row(row: Mapping, selection: Mapping) -> str | None:
    identity = row.get("original_identity") or {}
    if isinstance(identity, Mapping):
        for key in ("node_id", "graph_node_id"):
            value = identity.get(key)
            if isinstance(value, str) and value.startswith("co:"):
                return value
        ticker = identity.get("ticker")
        if isinstance(ticker, str) and ticker.strip():
            try:
                return company_node_id(_suite_for_selection(selection), ticker)
            except ValueError:
                return None
    return None


def _binding_fields(selection: Mapping, row: Mapping) -> dict[str, str]:
    return {
        "selection_id": row["selection_id"],
        "original_identity_sha256": content_sha256(row["original_identity"]),
        "selection_sha256": content_sha256(selection),
    }


def _adapter_envelope(
    *,
    owner_schema: str,
    receipt_ref: str,
    generation_id: str,
    effective_at: str,
    known_at: str,
    available_at: str,
    binding: Mapping[str, str],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "status": "OK",
        "qualification": "EXACT_PIT_QUERY",
        "owner_schema": owner_schema,
        "receipt_ref": receipt_ref,
        "generation_id": generation_id,
        "effective_at": effective_at,
        "known_at": known_at,
        "available_at": available_at,
        "valid_until": None,
        **binding,
        **payload,
    }
    body["receipt_sha256"] = content_sha256({k: v for k, v in body.items() if k != "receipt_sha256"})
    return body


def _late_for_known(available_at: str, known_at: str) -> bool:
    try:
        avail = dt.datetime.fromisoformat(available_at.replace("Z", "+00:00"))
        known = dt.datetime.fromisoformat(known_at.replace("Z", "+00:00"))
        if avail.tzinfo is None:
            avail = avail.replace(tzinfo=dt.timezone.utc)
        if known.tzinfo is None:
            known = known.replace(tzinfo=dt.timezone.utc)
        return avail.astimezone(dt.timezone.utc) > known.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return True


def _identity_payload(row: Mapping, *, historical: bool) -> dict[str, Any] | None:
    if row.get("resolution_state") != "RESOLVED" or not row.get("security_id"):
        return None
    security_id = str(row["security_id"])
    if not re.fullmatch(r"SEC:[^\s]+", security_id):
        return None
    node_id = str(row.get("node_id") or "")
    if not node_id.startswith("co:"):
        return None
    return {
        "security_id": security_id,
        "graph_node_ids": [node_id],
        "historical_identity_claim": historical is True,
    }


def _local_theme_fields(node_id: str, node_row: Mapping | None) -> dict[str, Any]:
    family, native = None, None
    if node_id.startswith("ltheme:"):
        parts = node_id.split(":", 2)
        if len(parts) == 3:
            family, native = parts[1], parts[2]
    if node_row:
        meta = node_row.get("source_meta")
        if isinstance(meta, str) and meta.strip():
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = None
        if isinstance(meta, Mapping):
            family = meta.get("source_family") or family
            native = meta.get("native_id") or native
    if family and native:
        node_id = local_theme_node_id(family, native)
    return {
        "node_id": node_id,
        "kind": "local_theme",
        "node_kind": "local_theme",
        "source_family": family,
        "native_id": native,
    }


def _canonical_for_local(
    edges: list[dict],
    local_node: str,
    *,
    asof: dt.date,
    cutoff: dt.date,
) -> tuple[list[str], list[dict]]:
    live, _ = _collapse_relevant_edges(edges, node_id=local_node, asof=asof, knowledge_cutoff=cutoff)
    theme_ids = sorted(
        {
            str(row["dst"])
            for row in live
            if str(row.get("type")) == "EXPRESSES"
            and str(row.get("src")) == local_node
            and str(row.get("dst") or "").startswith("theme:")
        }
    )
    nodes = [
        {
            "node_id": theme,
            "kind": "theme",
            "receipt_ref": f"theme_graph://canonical/{theme}",
            "receipt_sha256": hashlib.sha256(theme.encode()).hexdigest(),
        }
        for theme in theme_ids
    ]
    return theme_ids, nodes


def _knowledge_cutoff_date(known_at: str) -> dt.date:
    if "T" in known_at:
        return dt.datetime.fromisoformat(known_at.replace("Z", "+00:00")).date()
    return dt.date.fromisoformat(known_at[:10])


def _membership_rows(
    store_view: RepositoryStore,
    company_node: str,
    *,
    effective_at: str,
    known_at: str,
    rights_receipt_ref: str,
) -> list[dict]:
    asof = _parse_date(_asof_date(effective_at), "asof")
    cutoff = _knowledge_cutoff_date(known_at)
    nodes = _records(store_view.read_nodes())
    lifecycle = _records(store_view.read_node_lifecycle())
    node_map = _nodes_as_known(nodes, lifecycle, asof=asof, knowledge_cutoff=cutoff)
    edges = _records(store_view.read_edges())
    live, _ = _collapse_relevant_edges(
        edges, node_id=company_node, asof=asof, knowledge_cutoff=cutoff
    )
    rows: list[dict] = []
    for edge in live:
        if str(edge.get("type")) != "MEMBER_OF" or str(edge.get("src")) != company_node:
            continue
        concept = str(edge.get("dst") or "")
        if not concept.startswith("ltheme:"):
            continue
        concept_row = node_map.get(concept)
        fields = _local_theme_fields(concept, concept_row)
        canonical_ids, canonical_nodes = _canonical_for_local(edges, concept, asof=asof, cutoff=cutoff)
        family = fields.get("source_family")
        if family and rights.emission_allowed(str(family)):
            rights_status = "ALLOWED"
        else:
            rights_status = "REFUSED"
        refs = edge.get("evidence_refs")
        evidence_ref = refs[0] if isinstance(refs, list) and refs else f"theme_graph://edge/{edge.get('edge_id')}"
        if isinstance(evidence_ref, str):
            evidence_ref = evidence_ref
        else:
            evidence_ref = str(evidence_ref)
        rows.append(
            {
                "member_node_id": company_node,
                **fields,
                "canonical_node_ids": canonical_ids,
                "canonical_nodes": canonical_nodes,
                "evidence_ref": evidence_ref,
                "evidence_sha256": hashlib.sha256(evidence_ref.encode()).hexdigest(),
                "effective_from": _precise_timestamp(str(edge.get("valid_from") or asof.isoformat())),
                "effective_until": None
                if edge.get("valid_to") in (None, "", float("nan"))
                else _precise_timestamp(str(edge.get("valid_to")), end_of_day=True),
                "known_from": _precise_timestamp(str(edge.get("belief_time") or edge.get("evidence_time") or asof.isoformat())),
                "rights_status": rights_status,
                "rights_receipt_ref": rights_receipt_ref if rights_status == "ALLOWED" else rights_receipt_ref,
            }
        )
    return rows


def _load_state_artifact(data_dir: Path) -> dict | None:
    path = data_dir / "theme_graph" / STATE_ARTIFACT_NAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


@contextlib.contextmanager
def _bind_data_dir(root: Path):
    from lib import config

    previous = config.data_dir
    config.data_dir = lambda: root
    try:
        yield
    finally:
        config.data_dir = previous


def qualified_reads(
    selection: Mapping,
    *,
    data_dir=None,
    rights_path=None,
    now=None,
) -> dict:
    """Exact selection-clock reads for ``compose_selection_cohort``."""
    _ = now  # selection clocks only; never ambient now
    root = _repo_data_dir(data_dir)
    effective_at, known_at = _clock_pair(selection)
    rights_ref = _rights_receipt_ref(Path(rights_path) if rights_path else None)
    ctx = _bind_data_dir(root) if data_dir is not None else contextlib.nullcontext()
    with ctx:
        return _qualified_reads_inner(
            selection,
            root=root,
            effective_at=effective_at,
            known_at=known_at,
            rights_ref=rights_ref,
        )


COMPOSE_KEYS = ("identity_reads", "membership_reads", "state_reads")


def publication_reads(selection: Mapping, *, data_dir=None, rights_path=None) -> dict:
    """compose_selection_cohort kwargs for selection_cohort_publication (drops unqualified/selection_clock/owners)."""
    try:
        reads = qualified_reads(selection, data_dir=data_dir, rights_path=rights_path)
    except (OSError, ValueError, TypeError, KeyError):
        raise
    except Exception as exc:  # owner failure must stay inside the publication's honest-unavailable tuple
        raise ValueError(f"QUALIFIED_READS_OWNER_FAILURE:{type(exc).__name__}") from exc
    return {key: reads[key] for key in COMPOSE_KEYS}


def _qualified_reads_inner(
    selection: Mapping,
    *,
    root: Path,
    effective_at: str,
    known_at: str,
    rights_ref: str,
) -> dict:
    store_view = RepositoryStore()
    identity_reads: dict[str, dict] = {}
    membership_reads: dict[str, dict] = {}
    state_reads: dict[str, dict] = {}
    unqualified: list[dict] = []
    owners: dict[str, Any] = {
        "identity": {"owner": IDENTITY_OWNER_SCHEMA},
        "membership": {"owner": MEMBERSHIP_OWNER_SCHEMA},
        "state": {"owner": theme_state.READ_SCHEMA},
        "rights": {"receipt_ref": rights_ref},
    }
    asof = _asof_date(effective_at)
    state_artifact = _load_state_artifact(root)

    for row in selection["rows"]:
        sid = row["selection_id"]
        binding = _binding_fields(selection, row)
        company_node = _company_node_from_row(row, selection)
        if company_node is None:
            unqualified.append(
                {
                    "security_id": None,
                    "kind": "identity",
                    "reason_code": _REASON_OWNER,
                    "owner": IDENTITY_OWNER_SCHEMA,
                    "detail": "company graph node unavailable",
                }
            )
            continue
        try:
            resolution = ir.resolve_graph_node_identity(company_node, asof=asof)
        except ir.UnknownGraphNodeError:
            unqualified.append(
                {
                    "security_id": None,
                    "kind": "identity",
                    "reason_code": _REASON_OWNER,
                    "owner": IDENTITY_OWNER_SCHEMA,
                    "detail": company_node,
                }
            )
            continue
        id_payload = _identity_payload(resolution, historical=True)
        if id_payload is None:
            unqualified.append(
                {
                    "security_id": None,
                    "kind": "identity",
                    "reason_code": _REASON_OWNER,
                    "owner": IDENTITY_OWNER_SCHEMA,
                    "detail": resolution.get("resolution_state"),
                }
            )
            continue
        available_at = _precise_timestamp(str(resolution.get("computed_at") or effective_at))
        if _late_for_known(available_at, known_at):
            unqualified.append(
                {
                    "security_id": id_payload["security_id"],
                    "kind": "identity",
                    "reason_code": _REASON_STALE,
                    "owner": IDENTITY_OWNER_SCHEMA,
                    "detail": available_at,
                }
            )
            continue
        id_receipt = _adapter_envelope(
            owner_schema=IDENTITY_OWNER_SCHEMA,
            receipt_ref=f"theme_graph://identity_resolution/{company_node}@{asof}",
            generation_id=str(resolution.get("engine_version") or store.ENGINE_VERSION),
            effective_at=effective_at,
            known_at=known_at,
            available_at=available_at,
            binding=binding,
            payload=id_payload,
        )
        identity_reads[sid] = id_receipt

        try:
            memberships = _membership_rows(
                store_view,
                company_node,
                effective_at=effective_at,
                known_at=known_at,
                rights_receipt_ref=rights_ref,
            )
        except Exception:
            unqualified.append(
                {
                    "security_id": id_payload["security_id"],
                    "kind": "membership",
                    "reason_code": _REASON_OWNER,
                    "owner": MEMBERSHIP_OWNER_SCHEMA,
                    "detail": company_node,
                }
            )
            continue

        if not memberships:
            unqualified.append(
                {
                    "security_id": id_payload["security_id"],
                    "kind": "membership",
                    "reason_code": _REASON_NO_OVERLAP,
                    "owner": MEMBERSHIP_OWNER_SCHEMA,
                    "detail": company_node,
                }
            )

        mem_available = available_at
        mem_receipt = _adapter_envelope(
            owner_schema=MEMBERSHIP_OWNER_SCHEMA,
            receipt_ref=f"theme_graph://membership_pit/{company_node}@{asof}",
            generation_id=store.ENGINE_VERSION,
            effective_at=effective_at,
            known_at=known_at,
            available_at=mem_available,
            binding=binding,
            payload={
                "security_id": id_payload["security_id"],
                "complete": True,
                "memberships": memberships,
                "identity_receipt_ref": id_receipt["receipt_ref"],
                "identity_receipt_sha256": id_receipt["receipt_sha256"],
            },
        )
        if _late_for_known(mem_available, known_at):
            unqualified.append(
                {
                    "security_id": id_payload["security_id"],
                    "kind": "membership",
                    "reason_code": _REASON_STALE,
                    "owner": MEMBERSHIP_OWNER_SCHEMA,
                    "detail": mem_available,
                }
            )
        else:
            membership_reads[sid] = mem_receipt

        for member in memberships:
            concept_id = member["node_id"]
            if concept_id in state_reads:
                continue
            if state_artifact is None:
                unqualified.append(
                    {
                        "security_id": id_payload["security_id"],
                        "kind": "state",
                        "reason_code": _REASON_OWNER,
                        "owner": theme_state.READ_SCHEMA,
                        "detail": concept_id,
                    }
                )
                continue
            artifact_effective = str(state_artifact.get("effective_at") or effective_at)
            state_reads[concept_id] = theme_state.read_theme_state(
                state_artifact,
                concept_id,
                effective_at=artifact_effective,
                known_at=known_at,
                expected_generation_id=state_artifact.get("generation_id"),
            )
            if state_reads[concept_id].get("status") != "UNAVAILABLE":
                state_reads[concept_id]["effective_at"] = effective_at
                state_reads[concept_id]["known_at"] = known_at

    return {
        "identity_reads": identity_reads,
        "membership_reads": membership_reads,
        "state_reads": state_reads,
        "unqualified": unqualified,
        "selection_clock": {"effective_at": effective_at, "known_at": known_at},
        "owners": owners,
    }

