"""Read source-owned sector baskets and local parents without a classification master.

Only exact crosswalk-registered sector-context baskets qualify. These references
are not official issuer classifications and do not manufacture graph edges.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from engine.theme_graph.ontology import compose_neighborhood, _default_rights_resolver
from engine.theme_graph import rights
from engine.theme_graph.change_report import _display

CROSSWALK_PATH = Path(__file__).resolve().parents[2] / "config/theme_crosswalk.yml"
SCHEMA = "gmi.theme_structural_context/v1"
LIMITATIONS = [
    "Sector references are recorded memberships in owner-registered context baskets, not complete official company classifications.",
    "The latest stored crosswalk identifies references; graph clocks select memberships, not historical owner classifications.",
    "Source-local parent references retain recorded node metadata; they are not sector, industry or subindustry equivalence.",
    "No industry/subindustry owner is bound here. Missing references do not establish absence of a real classification.",
    "No graph mutation, canonical mapping, curation approval, public-display permission, ranking or trading authority.",
]


class _OwnerLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader, node):
    result = {}
    for key, value in loader.construct_pairs(node, deep=True):
        if key in result:
            raise ValueError("duplicate structural owner key")
        result[key] = value
    return result


_OwnerLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_structural_owner():
    """Read the incumbent crosswalk once; no alternate CLI-supplied registry."""
    with CROSSWALK_PATH.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("structural owner document exceeds 1 MiB")
    try:
        document = yaml.load(raw, Loader=_OwnerLoader)
    except yaml.YAMLError as exc:
        raise ValueError("unreadable structural owner document") from exc
    return document, hashlib.sha256(raw).hexdigest()


def _owner_index(document):
    if not isinstance(document, dict) or not isinstance(document.get("unmapped_baskets"), list):
        raise ValueError("structural owner requires the existing unmapped_baskets registry")
    index, seen = {}, set()
    for position, row in enumerate(document["unmapped_baskets"]):
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError("invalid structural owner reference")
        key = row["id"]
        if key in seen:
            raise ValueError("duplicate structural owner reference")
        seen.add(key)
        # The accepted owner census reserves this exact namespace for sector context.
        # A matching display label, sector leg, or unregistered basket is insufficient.
        if key.startswith("us_sector_"):
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                raise ValueError("structural owner reference lacks its declared meaning")
            index[key] = dict(reason=row["reason"], source_pointer=f"/unmapped_baskets/{position}")
    return index


def compose_structure(store_view, *, node_id, asof, knowledge_cutoff=None,
                      owner_document=None, owner_sha256=None, rights_resolver=None):
    if owner_document is None:
        owner_document, owner_sha256 = load_structural_owner()
    if not isinstance(owner_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", owner_sha256) is None:
        raise ValueError("structural owner digest required")
    index = _owner_index(owner_document)
    resolver = _default_rights_resolver if rights_resolver is None else rights_resolver
    neighborhood = compose_neighborhood(store_view, node_id=node_id, asof=asof,
        knowledge_cutoff=knowledge_cutoff, rights_resolver=resolver)
    def query(identity):
        return dict(node_id=identity, asof=neighborhood["asof"],
                    knowledge_cutoff=neighborhood["knowledge_cutoff"])
    def sector_reference(node):
        if not node or node["kind"] != "basket":
            return None
        external = node["external_ids"]
        key = external.get("basket_id")
        if (not isinstance(key, str) or key not in index or external.get("suite") != "baskets"
                or node["node_id"] != "basket:baskets:" + key):
            return None
        return dict(reference_kind="REGISTERED_SECTOR_CONTEXT_BASKET", node_id=node["node_id"],
            basket_id=key, owner_reason=index[key]["reason"], source_pointer=index[key]["source_pointer"],
            neighborhood_query=query(node["node_id"]), membership_evidence=[])
    def parent_reference(node, membership=None):
        if not node or node["kind"] != "local_theme":
            return None
        metadata = node.get("source_meta") or {}
        key = metadata.get("parent_source_key")
        if key is None or key == "":
            return None
        family = metadata.get("source_family")
        if (not isinstance(key, str) or not isinstance(family, str) or not family
                or family != rights.family_for_node_id(node["node_id"])
                or not isinstance(metadata.get("parent_source_label"), (str, type(None)))):
            raise ValueError("invalid source-local parent reference")
        return dict(reference_kind="SOURCE_LOCAL_PARENT_REFERENCE", local_node_id=node["node_id"],
            source_family=family, parent_source_key=key, parent_source_label=metadata.get("parent_source_label"),
            reference_basis="RECORDED_NODE_SOURCE_METADATA", rights=resolver(node["node_id"]),
            neighborhood_query=query(node["node_id"]), membership_evidence=[] if membership is None else [membership])
    subject = neighborhood["subject"]
    subject_reference = sector_reference(subject)
    sectors, parents, members = {}, {}, set()
    parent = parent_reference(subject)
    if parent:
        parents[parent["local_node_id"]] = parent
    for relation in neighborhood["relations"]:
        if relation["type"] != "MEMBER_OF":
            continue
        if relation["direction"] == "OUTGOING":
            sector = sector_reference(relation["peer"])
            if sector:
                record = sectors.setdefault(sector["node_id"], sector)
                record["membership_evidence"].append(relation)
            parent = parent_reference(relation["peer"], relation)
            if parent:
                existing = parents.get(parent["local_node_id"])
                if existing: existing["membership_evidence"].append(relation)
                else: parents[parent["local_node_id"]] = parent
        elif subject_reference and relation["direction"] == "INCOMING":
            peer = relation["peer"]
            if peer and peer["kind"] == "company":
                members.add(peer["node_id"])
    sector_rows = [sectors[key] for key in sorted(sectors)]
    parent_rows = [parents[key] for key in sorted(parents)]
    state = "SUBJECT_UNAVAILABLE" if subject is None else "REFERENCES_FOUND" if sector_rows or subject_reference else "NO_RECORDED_REFERENCE"
    return dict(schema=SCHEMA, authority_ceiling="research_internal_only", neighborhood=neighborhood,
        owner_reference_basis="LATEST_STORED_CROSSWALK", historical_classification_claim=False,
        historical_hierarchy_claim=False,
        owner_reference=dict(source_path="config/theme_crosswalk.yml", sha256=owner_sha256,
                             registered_sector_baskets=len(index)),
        subject_reference=subject_reference, sector_references=sector_rows, source_parent_references=parent_rows,
        member_queries=[query(key) for key in sorted(members)],
        counts=dict(sector_references=len(sector_rows), source_parent_references=len(parent_rows), member_queries=len(members)),
        coverage=dict(sector=dict(state=state, reason="Recorded sector-context references only; no complete classification claim."),
            industry=dict(state="OWNER_NOT_BOUND", reason="No accepted industry identity owner bound to this view."),
            subindustry=dict(state="OWNER_NOT_BOUND", reason="No accepted subindustry identity owner bound to this view.")),
        limitations=list(LIMITATIONS))


def render_markdown(result):
    n = result["neighborhood"]
    lines = ["# GMI structural references", "", _display(n["node_id"]),
        f"Graph effective date: {n['asof']}; knowledge cutoff: {n['knowledge_cutoff']}.",
        "Latest stored owner references; not official or historical company classification.", "",
        "## Recorded sector-context baskets"]
    refs = result["sector_references"] or ([result["subject_reference"]] if result["subject_reference"] else [])
    for row in refs:
        lines.append(_display(row["node_id"]) + " — " + _display(row["owner_reason"]))
    if not refs: lines.append("No recorded sector-context reference in this view.")
    lines += ["", "## Source-local parents"]
    for row in result["source_parent_references"]:
        lines.append(_display(row["local_node_id"]) + " → " + _display(row["source_family"] + ":" + row["parent_source_key"]))
    if not result["source_parent_references"]: lines.append("No recorded source-local parent reference.")
    lines += ["", "Industry: OWNER_NOT_BOUND. Subindustry: OWNER_NOT_BOUND.",
        "Exact neighborhood queries and original membership evidence are retained in JSON.", "", *LIMITATIONS, ""]
    return "\n".join(lines)


# Versioned owner read. The v1 contract and default CLI remain above, unchanged.
# This observes a current Stage fact; it is not a per-use rights grant.
from datetime import date, datetime, timezone
import json

V2_SCHEMA = "gmi.theme_structural_context/v2"
_OWNER_INPUTS = (
    "data/theme_graph/nodes.parquet",
    "data/theme_graph/identity_resolution.parquet",
    "data/reference/security_master.parquet",
    "data/reference/vendor_aliases.parquet",
    "data/reference/_receipt.json",
    "data/stage_analysis/screener.json",
    "data/stage_analysis/industry_ranks.json",
)


class _OwnerUnavailable(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _utc_now():
    return datetime.now(timezone.utc)


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _precise_clock(value, now):
    # A date-only emission cannot establish availability within the current day.
    if not isinstance(value, str) or "T" not in value:
        raise _OwnerUnavailable("OWNER_EMISSION_CLOCK_UNPROVEN")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise _OwnerUnavailable("OWNER_EMISSION_CLOCK_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _OwnerUnavailable("OWNER_EMISSION_CLOCK_INVALID")
    if parsed > now:
        raise _OwnerUnavailable("OWNER_NOT_YET_EMITTED")
    return parsed.astimezone(timezone.utc)


def _source_clock(value, now):
    if not isinstance(value, str):
        raise _OwnerUnavailable("OWNER_SOURCE_CLOCK_UNAVAILABLE")
    if "T" in value:
        return _precise_clock(value, now)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _OwnerUnavailable("OWNER_SOURCE_CLOCK_INVALID") from exc
    if parsed > now.date():
        raise _OwnerUnavailable("OWNER_SOURCE_CLOCK_FUTURE")
    return parsed


def _observe_inputs(root):
    observations = {}
    for relative in _OWNER_INPUTS:
        path = root / relative
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            observations[relative] = {"state": "MISSING", "sha256": None, "bytes": None}
        else:
            observations[relative] = {
                "state": "OBSERVED", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
            }
    return observations


def _owner_document(root, relative):
    try:
        value = json.loads((root / relative).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _OwnerUnavailable("OWNER_ARTIFACT_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise _OwnerUnavailable("OWNER_ARTIFACT_INVALID")
    return value


def _identity_receipt(node_id, root, now):
    from engine.theme_graph import identity_resolution as identity_owner, store as graph_owner
    from lib import config

    # The graph bridge and fixed Data OS runtime must address the same estate.
    if Path(config.data_dir()).resolve() != (root / "data").resolve():
        raise _OwnerUnavailable("OWNER_SOURCE_ESTATE_MISMATCH")
    identity = identity_owner.resolve_graph_node_identity(node_id, asof=None)
    if isinstance(identity, dict):
        identity = dict(identity)
        # Nullable owner axes survive pandas parquet null representation.
        # This cannot repair a missing security/listing or invent an issuer.
        for field in ("issuer_id", "refusal_reason"):
            value = identity.get(field)
            if isinstance(value, float) and value != value:
                identity[field] = None
    if not isinstance(identity, dict) or (
        identity.get("schema") != identity_owner.SCHEMA_ID
        or identity.get("node_id") != node_id
        or identity.get("graph_kind") != "company"
        or identity.get("market_scope") != "us"
        or identity.get("resolution_state") != "RESOLVED"
        or not isinstance(identity.get("security_id"), str)
        or not isinstance(identity.get("listing_key"), str)
    ):
        raise _OwnerUnavailable("GRAPH_IDENTITY_UNAVAILABLE")
    if identity.get("resolution_asof") != now.date().isoformat():
        raise _OwnerUnavailable("GRAPH_IDENTITY_NOT_CURRENT")
    computed = _precise_clock(identity.get("computed_at"), now)
    master_emitted = _precise_clock(identity.get("master_generated_at"), now)
    if computed.date() != now.date() or master_emitted > computed:
        raise _OwnerUnavailable("GRAPH_IDENTITY_CLOCK_ORDER_UNPROVEN")
    if identity.get("refusal_reason") is not None:
        raise _OwnerUnavailable("GRAPH_IDENTITY_CONTRADICTORY_DISPOSITION")
    receipt = _owner_document(root, "data/reference/_receipt.json")
    _precise_clock(receipt.get("generated_at"), now)
    _source_clock(receipt.get("symbol_directory_snapshot"), now)
    if (
        identity.get("master_generated_at") != receipt.get("generated_at")
        or identity.get("master_symbol_directory_snapshot") != receipt.get("symbol_directory_snapshot")
        or identity.get("master_code_version") != receipt.get("code_version")
    ):
        raise _OwnerUnavailable("GRAPH_IDENTITY_SOURCE_RECEIPT_MISMATCH")

    # Recheck through the incumbent owner's public current derivation, not a
    # second allocator or a downstream symbol join. A stale/corrupt sidecar may
    # name a different valid SEC; normalizing that SEC alone would not detect it.
    nodes = graph_owner.read_nodes().to_dict("records")
    selected = [row for row in nodes if row.get("node_id") == node_id]
    if len(selected) != 1:
        raise _OwnerUnavailable("GRAPH_SUBJECT_AMBIGUOUS")
    owner_nodes = selected + [row for row in nodes if row.get("kind") == "etf"]
    current_rows = identity_owner.derive_rows(
        owner_nodes, resolution_asof=now.date().isoformat(), computed_at=_stamp(now),
        engine_version=graph_owner.ENGINE_VERSION, data_dir=root / "data",
    )
    if len(current_rows) != 1:
        raise _OwnerUnavailable("GRAPH_IDENTITY_OWNER_RECHECK_UNAVAILABLE")
    current = current_rows[0]
    keys = tuple(key for key in graph_owner.IDENTITY_RESOLUTION_COLUMNS
                 if key not in {"computed_at", "engine_version"})
    if set(identity) != set(graph_owner.IDENTITY_RESOLUTION_COLUMNS):
        raise _OwnerUnavailable("GRAPH_IDENTITY_WIRE_INVALID")
    if any(identity.get(key) != current.get(key) for key in keys):
        raise _OwnerUnavailable("GRAPH_IDENTITY_OWNER_RECHECK_MISMATCH")
    # JSON-compatible owner row only; pandas scalar nulls are not identities.
    from engine.intelligence_workspace.contracts import canonical_json_bytes
    canonical_json_bytes(identity)
    return identity


def _industry_receipt(identity, root, now):
    from engine.intelligence_workspace.contracts import EntityRequest, canonical_json_sha256
    from engine.intelligence_workspace.runtime import build_runtime

    runtime = build_runtime(repo_root=root)
    from engine.intelligence_workspace.adapters.stage import StageAdapter
    from engine.intelligence_workspace.entity import DataOSIdentityNormalizer
    stage = runtime.adapters.get("stage")
    if (not isinstance(stage, StageAdapter) or stage.path != root / "data/stage_analysis/screener.json"
            or stage.vendor != "store" or stage._injected_symbol_map_loader is not None
            or not isinstance(runtime.identity_normalizer, DataOSIdentityNormalizer)
            or runtime.identity_normalizer.root != root):
        raise _OwnerUnavailable("FIXED_OWNER_COMPOSITION_MISMATCH")
    normalized = runtime.identity_normalizer.normalize_many(
        (EntityRequest(type="security", id=identity["security_id"]),)
    )
    if len(normalized) != 1 or (
        normalized[0].type != "security" or normalized[0].id != identity["security_id"]
        or normalized[0].universe != "us_equity" or normalized[0].state != "active"
    ):
        raise _OwnerUnavailable("DATAOS_SECURITY_NOT_ACTIVE")
    relationship = runtime.resolve_current_industry_relationship(normalized[0])
    expected = {"schema", "registry_digest", "relationship", "from", "to", "status", "reason_code",
                "observed_at", "effective_at", "as_of", "generated_at", "freshness", "quality",
                "source", "provenance", "audience", "consumer_use", "relationship_fingerprint"}
    if not isinstance(relationship, dict) or set(relationship) != expected:
        raise _OwnerUnavailable("INDUSTRY_OWNER_WIRE_INVALID")
    if relationship["audience"] != "subscriber" or relationship["consumer_use"] != "ai_fact":
        raise _OwnerUnavailable("INDUSTRY_OWNER_PROJECTION_MISMATCH")
    nested_keys = {
        "source": {"source_id", "owner", "license_class", "dataset_id"},
        "provenance": {"kind", "owner_field_key", "relationship", "basis"},
        "freshness": {"state", "policy"}, "quality": {"state", "issues"},
    }
    if any(not isinstance(relationship.get(key), dict)
           or set(relationship[key]) != keys for key, keys in nested_keys.items()):
        raise _OwnerUnavailable("INDUSTRY_OWNER_WIRE_INVALID")
    source = relationship["source"]
    provenance = relationship["provenance"]
    if (
        relationship.get("schema") != "intelligence_workspace.current_industry_relationship.v1"
        or relationship.get("registry_digest") != runtime.registry.digest
        or relationship.get("relationship") != "security.current_industry"
        or relationship.get("from") != {"type": "security", "id": identity["security_id"]}
        or source.get("source_id") != "stage_analysis.screener"
        or source.get("owner") != "stage_analysis"
        or provenance.get("kind") != "owner_relationship"
        or provenance.get("relationship") != "security.current_industry"
        or provenance.get("owner_field_key") != "current_industry"
        or provenance.get("basis") != "owner_published_current_relationship"
    ):
        raise _OwnerUnavailable("INDUSTRY_OWNER_BINDING_MISMATCH")
    basis = {key: value for key, value in relationship.items()
             if key not in {"generated_at", "relationship_fingerprint"}}
    if relationship.get("relationship_fingerprint") != canonical_json_sha256(basis):
        raise _OwnerUnavailable("INDUSTRY_OWNER_FINGERPRINT_MISMATCH")
    # The owner's subscriber projection removes artifact_id and owner_artifact.
    # Their binding is the fixed Stage reader, not this projected receipt.
    _precise_clock(relationship.get("generated_at"), _utc_now())
    if relationship.get("status") != "available":
        raise _OwnerUnavailable("INDUSTRY_OWNER_" + str(relationship.get("reason_code") or "UNAVAILABLE").upper())
    if (
        relationship.get("reason_code") is not None
        or (relationship.get("freshness") or {}).get("state") != "fresh"
        or (relationship.get("freshness") or {}).get("policy") != "owner_native"
        or (relationship.get("quality") or {}).get("state") != "ok"
        or (relationship.get("quality") or {}).get("issues") != []
    ):
        raise _OwnerUnavailable("INDUSTRY_OWNER_NOT_CURRENT")
    target = relationship.get("to")
    if not isinstance(target, dict) or set(target) != {"type", "id", "universe"} or (
        target.get("type") != "industry" or target.get("universe") != "us_industry"
        or not isinstance(target.get("id"), str) or not target["id"]
        or target["id"] != target["id"].strip()
    ):
        raise _OwnerUnavailable("INDUSTRY_TARGET_INVALID")
    # Validate this fixed target registry before the incumbent normalizer reads
    # its containers. Malformed owner JSON is a typed refusal, not an attribute
    # error or a substitute identity source.
    target_document = _owner_document(root, "data/stage_analysis/industry_ranks.json")
    regions = target_document.get("regions")
    if not isinstance(regions, dict) or not isinstance(regions.get("USA"), list):
        raise _OwnerUnavailable("INDUSTRY_TARGET_REGISTRY_SHAPE_INVALID")
    normalized_target = runtime.identity_normalizer.normalize_many(
        (EntityRequest(type="industry", id=target["id"]),)
    )
    if len(normalized_target) != 1 or (
        normalized_target[0].type != "industry" or normalized_target[0].id != target["id"]
        or normalized_target[0].universe != "us_industry" or normalized_target[0].state != "active"
    ):
        raise _OwnerUnavailable("INDUSTRY_TARGET_NOT_REGISTERED")
    for relative, schema in (
        ("data/stage_analysis/screener.json", "stage_screener.v1"),
        ("data/stage_analysis/industry_ranks.json", "stage_industry_ranks.v1"),
    ):
        document = _owner_document(root, relative)
        if document.get("schema") != schema:
            raise _OwnerUnavailable("INDUSTRY_ARTIFACT_SCHEMA_INVALID")
        if document.get("asof") != now.date().isoformat():
            raise _OwnerUnavailable("INDUSTRY_ARTIFACT_NOT_CURRENT")
        _precise_clock(document.get("built"), _utc_now())
        if relative.endswith("screener.json"):
            _source_clock(document.get("stage_week_end"), now)
    if relationship.get("as_of") != now.date().isoformat():
        raise _OwnerUnavailable("INDUSTRY_RELATIONSHIP_NOT_CURRENT")
    for field in ("observed_at", "effective_at"):
        _source_clock(relationship.get(field), now)
    return relationship


def compose_structure_v2(store_view, *, node_id, asof, knowledge_cutoff=None,
                         owner_document=None, owner_sha256=None, rights_resolver=None):
    """Read current US industry through the existing identity/Stage owners.

    Availability is an observed source fact, not an entitlement, historical
    classification, raw-byte authentication, issuer-wide taxonomy, or graph edge.
    There is no injected relationship/identity/rights qualification callback.
    """
    from engine.theme_graph.ontology import RepositoryStore

    legacy = compose_structure(
        store_view, node_id=node_id, asof=asof, knowledge_cutoff=knowledge_cutoff,
        owner_document=owner_document, owner_sha256=owner_sha256, rights_resolver=rights_resolver,
    )
    started = _utc_now()
    _precise_clock(_stamp(started), started)
    fact = dict(
        availability=dict(state="UNAVAILABLE", reason_codes=["OWNER_NOT_READ"]),
        identity=None, industry_reference=None, input_observation=None,
    )
    result = dict(
        schema=V2_SCHEMA, context_v1=legacy, owner_structure=fact,
        query=dict(node_id=node_id, effective_at=legacy["neighborhood"]["asof"],
                   known_at=legacy["neighborhood"]["knowledge_cutoff"], clock_precision="date"),
        read_clock=dict(started_at=_stamp(started), finished_at=None),
        subindustry=dict(state="OWNER_NOT_BOUND", reason_codes=["NO_STABLE_SUBINDUSTRY_OWNER_CONTRACT"]),
        use_qualification=dict(
            status="NOT_QUALIFIED", rights_state="OWNER_NOT_BOUND",
            reason_codes=["STAGE_RELATIONSHIP_PER_USE_RIGHTS_UNSUPPORTED"],
            authorized_uses=[], public_display=False, machine_qualified=False, predictive_use=False,
        ),
        authority_flags=dict(rank=False, gate=False, size=False, insertion=False,
                             origination=False, escalation=False, predictive_use=False),
        limitations=[
            "The current security relationship does not classify every business of its nullable issuer.",
            "Read time and separately observed bytes are not classification first-known evidence.",
            "Date-only owner clocks retain their precision; no historical classification claim.",
            "The existing ThemeRightsProjector accepts graph-node rights only; it does not grant Stage relationship use.",
            "Subindustry owner binding, historical/rights/coverage qualification and natural reader consumption remain unavailable.",
        ],
    )
    subject = legacy["neighborhood"]["subject"]
    try:
        if subject is None:
            raise _OwnerUnavailable("SUBJECT_UNAVAILABLE")
        if subject.get("kind") != "company" or subject.get("market_scope") != "us":
            fact["availability"] = dict(state="UNSUPPORTED_SUBJECT", reason_codes=["SINGLE_US_SECURITY_OWNER_REQUIRED"])
            return result
        current_day = started.date().isoformat()
        if result["query"]["effective_at"] != current_day or result["query"]["known_at"] != current_day:
            raise _OwnerUnavailable("CURRENT_ONLY_QUERY_REQUIRED")
        if not isinstance(store_view, RepositoryStore):
            raise _OwnerUnavailable("INCUMBENT_REPOSITORY_STORE_REQUIRED")
        root = _repo_root()
        before = _observe_inputs(root)
        fact["input_observation"] = dict(
            basis="SEPARATELY_OBSERVED_BEFORE_AFTER_OWNER_READ", consumed_bytes_proven=False,
            artifacts=before, unchanged_during_read=False,
        )
        identity = _identity_receipt(node_id, root, started)
        fact["identity"] = identity
        relationship = _industry_receipt(identity, root, started)
        after = _observe_inputs(root)
        if after != before:
            fact["identity"] = None
            raise _OwnerUnavailable("OWNER_INPUT_CHANGED_DURING_READ")
        fact["input_observation"]["unchanged_during_read"] = True
        fact["identity"] = identity
        fact["industry_reference"] = dict(
            target=relationship["to"], security_id=identity["security_id"],
            owner_relationship=relationship, historical_classification_claim=False,
            classification_first_known_at=None,
            owner_binding=dict(
                graph_reader="engine.theme_graph.identity_resolution.resolve_graph_node_identity",
                identity_reader="engine.intelligence_workspace.entity.DataOSIdentityNormalizer.normalize_many",
                relationship_reader="engine.intelligence_workspace.resolver.DatapointResolver.resolve_current_industry_relationship",
                artifact_id="data/stage_analysis/screener.json",
                target_identity_artifact_id="data/stage_analysis/industry_ranks.json",
                supported_scope="CURRENT_US_SECURITY_INDUSTRY",
            ),
        )
        fact["availability"] = dict(state="AVAILABLE", reason_codes=[])
    except _OwnerUnavailable as exc:
        fact["availability"] = dict(state="UNAVAILABLE", reason_codes=[exc.code])
    except (OSError, ValueError, TypeError, RuntimeError, KeyError):
        # Missing/unrecognized owner results are explicit refusals, never "none".
        fact["availability"] = dict(state="UNAVAILABLE", reason_codes=["OWNER_READ_UNAVAILABLE"])
    finally:
        finished = _utc_now()
        result["read_clock"]["finished_at"] = _stamp(finished)
        if finished < started:
            fact["availability"] = dict(state="UNAVAILABLE", reason_codes=["READER_CLOCK_REGRESSED"])
            fact["identity"] = None
            fact["industry_reference"] = None
    return result


def render_markdown_v2(result):
    fact = result["owner_structure"]
    lines = [render_markdown(result["context_v1"]).rstrip(), "",
             "## Current security industry owner observation",
             "Availability: " + fact["availability"]["state"] + "."]
    if fact["industry_reference"]:
        ref = fact["industry_reference"]
        lines.append(_display(ref["security_id"]) + " → " + _display(ref["target"]["id"]))
        lines.append("Owner source clock: " + _display(ref["owner_relationship"]["observed_at"]))
    else:
        lines.append("Reasons: " + ", ".join(fact["availability"]["reason_codes"]))
    lines += ["Use: NOT_QUALIFIED; rights: OWNER_NOT_BOUND. Public, machine-qualified and predictive use: false.",
              "Subindustry: OWNER_NOT_BOUND.", *result["limitations"], ""]
    return "\n".join(lines)
