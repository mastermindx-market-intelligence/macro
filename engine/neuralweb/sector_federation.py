"""Pure Technology owner composition; controlled source support, not publication.

§0/§9: historical Task1/waiver are DO_NOT_REDO. Existing owners retain
identity, PIT, rights, classification, state and publication. No acquisition,
scheduler, output or financial decision authority is created here.

Parent's explicit Task2 ruling permits only incumbent deterministic frozen
schema-source reads needed for validation. Domain/input filesystem, network,
wall-clock, model/provider and output effects remain forbidden. Caller-supplied
receipts/clocks and qualified optional reads are assertions of their owners;
this module never reconstructs raw source hashes or launders rights.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date, timedelta
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from engine.sector_intelligence import contracts as owner

_DIMENSION_ORDER = (
    "sector_slow_clock", "sector_fast_tape", "sector_participation",
    "sector_concentration", "subsector_entry", "closed_session_leadership",
    "theme_health", "group_entry_context",
)
_SOURCE_KEYS = {
    "site-baskets": "baskets", "site-action-board": "action_board",
    "site-sector-central": "sector_central",
    "site-subsector-confluence": "subsector_confluence",
    "site-subsector-rotation": "subsector_rotation",
    "site-theme-state": "theme_state", "theme-crosswalk": "theme_crosswalk",
    "sp500-heatmap": "heatmap", "site-theme-lanes": "optional_entry_context",
}
_CAPS = {
    "is_context_only": True, "may_rank": False, "may_gate": False,
    "may_size": False, "may_escalate": False, "may_trade": False,
    "may_modify_prophet": False,
}
_DENIALS = [
    "originate_signal", "raise_authority_from_llm", "rank_security",
    "select_security", "size_position", "gate_decision", "execute_trade",
]
_LABELS = {
    "sector_slow_clock": ("Sector slow clock", "板块慢周期"),
    "sector_fast_tape": ("Sector fast tape", "板块快线"),
    "sector_participation": ("Sector participation", "板块参与度"),
    "sector_concentration": ("Heatmap concentration", "热图集中度"),
    "subsector_entry": ("Structural child entry", "结构子板块入场"),
    "closed_session_leadership": ("Closed-session leadership", "收盘后领涨"),
    "theme_health": ("Connected theme health", "关联主题健康"),
    "group_entry_context": ("Group entry context", "组级入场背景"),
}


class FederationError(RuntimeError):
    """Composition refused without producing or writing an artifact."""


class UnsupportedSector(FederationError):
    """Only the accepted exact Technology reference sector is admitted."""


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _fail(message):
    raise FederationError(message)


def _native_object(parent, field):
    """Retain a nullable native object; refuse malformed shapes explicitly."""
    value = parent.get(field)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        _fail(f"native {field} must be an object or truthful null")
    return value


def _payload_date(value):
    first, second = value.get("as_of"), value.get("asof")
    if first is not None and second is not None and first != second:
        _fail("owner as_of/asof fields disagree")
    return first if first is not None else second


def _source_ref_ok(ref, receipts):
    return isinstance(ref, str) and any(
        row["state"] == "available"
        and (ref == row["path"] or ref.startswith(row["path"] + "#/"))
        for row in receipts
    )


def _checked_mapping(value):
    if not isinstance(value, Mapping):
        _fail("FederationInputs requires an injected mapping")
    try:
        owner.canonical_json_bytes(value)
    except (owner.ContractError, ValueError, TypeError, RecursionError) as exc:
        raise FederationError("inputs must be finite acyclic JSON owner facts") from exc
    data = copy.deepcopy(dict(value))
    receipts = data.get("input_receipts")
    if not isinstance(receipts, list):
        _fail("input_receipts must be an injected array")
    # Reuse the one owned definition and semantic policy, not a local clone.
    registry = owner.ContractRegistry()
    receipt_schema = registry.schema_for("sector_dossier_read_model.v2")["$defs"]["input_receipt"]
    validator = Draft202012Validator(receipt_schema, format_checker=owner._FORMAT_CHECKER)
    for row in receipts:
        errors = list(validator.iter_errors(row))
        if errors:
            _fail("invalid shared v2 receipt: " + errors[0].message)
    issues = owner._v2_receipt_issues(receipts, path="$.input_receipts", cutoff=None)
    if issues:
        _fail("; ".join(str(issue) for issue in issues))
    by_id = {row["source_id"]: row for row in receipts}
    if set(by_id) != set(_SOURCE_KEYS):
        _fail("every declared source, including missing optional context, needs a receipt")
    for source_id, key in _SOURCE_KEYS.items():
        payload = data.get(key)
        receipt = by_id[source_id]
        if receipt["state"] == "available":
            if not isinstance(payload, Mapping):
                _fail(f"available {source_id} requires its injected native object")
            if receipt["freshness_role"] != "static_config" and _payload_date(payload) != receipt["as_of"]:
                _fail(f"{source_id} payload date must equal its supplied receipt date")
        elif payload is not None:
            _fail(f"unavailable {source_id} cannot supply available domain facts")
    board = data["action_board"]
    if board.get("schema") != "sector_intelligence_action_board.v1":
        _fail("existing action-board owner's stamped wrapper is required")
    if not isinstance(board.get("action_board"), Mapping):
        _fail("action_board must retain the native wrapped lane object")
    if owner._v2_timestamp(board.get("generated_utc")) is None:
        _fail("action board requires the owner's aware generated_utc; no cosmetic stamp")
    if owner._v2_timestamp(board["generated_utc"]) != owner._v2_timestamp(by_id["site-action-board"]["observed_at"]):
        _fail("action-board receipt must bind its actual owner generation instant")
    if board.get("baskets_sha256") != by_id["site-baskets"]["sha256"]:
        _fail("action board must bind the exact supplied basket byte receipt")
    if not isinstance(data["sector_central"].get("sectors"), list):
        _fail("sector_central requires native sectors[]")
    rows = [row for row in data["sector_central"]["sectors"] if isinstance(row, Mapping) and row.get("id") == "xlk"]
    if len(rows) != 1 or rows[0].get("ticker") != "XLK" or rows[0].get("kind") != "sector":
        _fail("one exact native xlk/XLK sector record is required")
    for key, field in (("subsector_confluence", "subsectors"), ("subsector_rotation", "subsectors"),
                       ("subsector_rotation", "themes"), ("theme_state", "themes"), ("theme_crosswalk", "themes"),
                       ("heatmap", "tiles")):
        if not isinstance(data[key].get(field), list):
            _fail(f"{key}.{field} must retain its native owner array")
    for key in ("optional_leadership", "same_horizon_owner_read"):
        read = data.get(key)
        if read is not None:
            if not isinstance(read, Mapping) or not _source_ref_ok(read.get("source_ref"), receipts):
                _fail(f"{key} requires an injected qualified read with admitted source reference")
            for field in ("scope", "horizon", "state", "as_of"):
                if not isinstance(read.get(field), str) or not read[field]:
                    _fail(f"{key} requires exact owner {field}")
            try:
                read_date = date.fromisoformat(read["as_of"])
            except ValueError as exc:
                raise FederationError(f"{key} has malformed owner date") from exc
            bound = next(row for row in receipts
                         if read["source_ref"] == row["path"]
                         or read["source_ref"].startswith(row["path"] + "#/"))
            if (bound["freshness_role"] != "market_observation"
                    or bound["as_of"] is None
                    or read_date > date.fromisoformat(bound["as_of"])):
                _fail(f"{key} cannot claim facts newer than its qualified market receipt")
    leadership = data.get("optional_leadership")
    if leadership is not None:
        rotation_receipt = by_id["site-subsector-rotation"]
        if (leadership["scope"] != "subsector" or leadership["horizon"] != "closed_session"
                or leadership["as_of"] != rotation_receipt["as_of"]
                or not (leadership["source_ref"] == rotation_receipt["path"]
                        or leadership["source_ref"].startswith(rotation_receipt["path"] + "#/"))):
            _fail("optional leadership must retain the qualified subsector rotation scope, horizon and date")
    cursors = data.get("owner_watermarks") or {}
    if not isinstance(cursors, Mapping) or not set(cursors).issubset(by_id):
        _fail("owner cursors must bind declared source IDs")
    if any(value is not None and not isinstance(value, str) for value in cursors.values()):
        _fail("owner-native cursors are strings or truthful nulls")
    data["input_receipts"] = sorted(receipts, key=lambda row: row["source_id"])
    return data


@dataclass(frozen=True)
class FederationInputs:
    baskets: Mapping[str, Any]
    action_board: Mapping[str, Any]
    sector_central: Mapping[str, Any]
    subsector_confluence: Mapping[str, Any]
    subsector_rotation: Mapping[str, Any]
    theme_state: Mapping[str, Any]
    theme_crosswalk: Mapping[str, Any]
    heatmap: Mapping[str, Any]
    input_receipts: tuple[Mapping[str, Any], ...]
    optional_leadership: Mapping[str, Any] | None = None
    optional_entry_context: Mapping[str, Any] | None = None
    same_horizon_owner_read: Mapping[str, Any] | None = None
    owner_watermarks: Mapping[str, str | None] | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FederationInputs":
        """Freeze injected native facts; do not acquire source bytes or clocks."""
        data = _checked_mapping(value)
        return cls(**{key: _freeze(data.get(key)) for key in cls.__dataclass_fields__})


def _dimension(name, *, source, as_of, scope, horizon, state, value, coverage="complete"):
    en, zh = _LABELS[name]
    unavailable = state == "unavailable"
    return {
        "dimension_id": name, "owner": source[0], "scope": scope, "horizon": horizon,
        "state": state, "label_en": en, "label_zh": zh,
        "summary_en": "Owner evidence is unavailable." if unavailable else "Preserved owner facts; descriptive context only.",
        "summary_zh": "负责方证据不可用。" if unavailable else "保留负责方事实，仅作描述性背景。",
        "value": value, "as_of": as_of, "coverage_state": "unavailable" if unavailable else coverage,
        "source_ref": source[1], "authority": copy.deepcopy(_CAPS),
    }


def _participation(sector, common):
    heat = _native_object(sector, "heat")
    adv, dec, pct = (heat.get(key) for key in ("adv", "dec", "breadth_pct"))
    for count in (adv, dec):
        if count is not None and (type(count) is not int or count < 0):
            _fail("native adv/dec counts must be nonnegative integers or null")
    if pct is not None and (type(pct) not in (int, float) or not 0 <= pct <= 100):
        _fail("owner participation percentage must retain its finite percent unit")
    total = adv + dec if adv is not None and dec is not None else None
    return {
        "method": "advancing_member_share", "state": "measured" if pct is not None else "unavailable",
        "value_pct": pct, "n_advancing": adv, "n_declining": dec, "n_total": total,
        "as_of": common, "source_ref": "site/sectordata/sector_central.json#/sectors/xlk/heat",  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        "display_only": True,
    }


def _concentration(heatmap):
    if heatmap.get("size_basis") != "marketcap":
        _fail("only owner marketcap heatmap sizes qualify this concentration method")
    seen = set()
    tiles = []
    for row in heatmap["tiles"]:
        if not isinstance(row, Mapping):
            _fail("native heatmap tiles must be objects")
        identity, sector = row.get("t"), row.get("sector")
        if (not isinstance(identity, str) or not identity.strip()
                or not isinstance(sector, str) or not sector.strip()):
            _fail("native heatmap tiles require exact nonempty t and sector identities")
        if identity in seen:
            _fail("duplicate native heatmap member identity")
        seen.add(identity)
        value = row.get("size")
        if value is not None and (type(value) not in (int, float) or value < 0):
            _fail("native heatmap size must be a finite nonnegative marketcap or null")
        if sector == "Technology":
            tiles.append(row)
    sizes = []
    for row in tiles:
        value = row.get("size")
        if value is not None:
            if type(value) not in (int, float) or value < 0:
                _fail("heatmap size must be a finite nonnegative marketcap or null")
            if value > 0:
                sizes.append(value)
    total = sum(sizes)
    # A missing size is not a zero and cannot silently narrow the population.
    missing = sum(row.get("size") is None for row in tiles)
    value = sum(sorted(sizes, reverse=True)[:5]) / total if total > 0 and not missing else None
    return {
        "method": "market_cap_top5_share", "state": "measured" if value is not None else "unavailable",
        "value": value, "n_members": len(tiles), "source_ref": "site/marketdata/sp500_heatmap.json#/tiles",  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        "display_only": True,
    }


def _children(data):
    rows = []
    for row in data["subsector_confluence"]["subsectors"]:
        if not isinstance(row, Mapping):
            _fail("native structural child rows must be objects")
        if row.get("sector") != "Technology":
            continue
        if (row.get("kind") != "subsector" or not isinstance(row.get("key"), str)
                or not row["key"] or row.get("as_of") != _payload_date(data["subsector_confluence"])):
            _fail("Technology children must retain exact subsector grain and owner source date")
        rows.append(row)
    keys = [row["key"] for row in rows]
    if len(keys) != len(set(keys)):
        _fail("duplicate native structural child key")
    result = []
    for row in sorted(rows, key=lambda value: value.get("key", "")):
        entry, regime = _native_object(row, "entry"), _native_object(row, "regime")
        key = row.get("key")
        result.append({
            "child_id": f"subsector:{key}", "native_key": key,
            "name_en": row.get("label"), "name_zh": row.get("label_zh") or "",
            "href": f"basket/subsector_{key}.html", "relationship_basis": "structural_child",
            "class": row.get("class"), "entry_tier": entry.get("tier"),
            "regime_state": regime.get("state"), "reliability": row.get("reliability"),
            "n_priced": row.get("n_priced"), "n_members": row.get("n_members"),
            "as_of": row.get("as_of"), "source_ref": f"site/marketdata/subsector_confluence.json#/subsectors/{key}",  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        })
    return result


def _connected_themes(data, children):
    child_keys = {row["native_key"] for row in children}
    states = {}
    for row in data["theme_state"]["themes"]:
        if not isinstance(row, Mapping):
            _fail("theme-state rows must be native objects")
        key = row.get("theme_id")
        if not isinstance(key, str) or not key:
            _fail("theme health requires the owner's native theme_id")
        if key in states:
            _fail("duplicate owner theme ID")
        states[key] = row
    seen = set()
    result = []
    for row in data["theme_crosswalk"]["themes"]:
        if not isinstance(row, Mapping):
            _fail("governed crosswalk rows must be objects")
        key = row.get("id")
        if not isinstance(key, str) or not key:
            _fail("governed crosswalk requires its owner's native id")
        if not isinstance(row.get("subsector_keys"), list) or any(
                not isinstance(item, str) or not item for item in row["subsector_keys"]):
            _fail("crosswalk structural references must retain exact owner keys")
        if key in seen:
            _fail("duplicate governed crosswalk theme ID")
        seen.add(key)
        matches = sorted(child_keys.intersection(row.get("subsector_keys") or []))
        if not matches:
            continue  # No label/case/approximate mapping or structural-grain inference.
        state = states.get(key)
        if state is None:
            continue  # A configuration relation alone supplies no available health fact.
        foresight = state.get("foresight")
        if (not isinstance(foresight, Mapping) or not isinstance(foresight.get("stage"), str)
                or type(foresight.get("entry_ready")) is not bool):
            _fail("connected health requires explicit owner stage and entry_ready; no invented false")
        stage = foresight["stage"]
        result.append({
            "theme_id": key, "name_en": row.get("name_en"), "name_zh": row.get("name_zh") or "",
            "href": f"theme/{key}.html", "relationship_basis": "theme_crosswalk.subsector_keys",
            "matched_child_key": matches[0], "primary_basket_id": row.get("primary_basket_id"),
            "stage": stage, "entry_ready": foresight["entry_ready"],
            "as_of": _payload_date(data["theme_state"]),
            "source_refs": [f"config/theme_crosswalk.yml#/themes/{key}", f"site/neuralwebdata/theme_state.json#/themes/{key}"],  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        })
    return sorted(result, key=lambda row: row["theme_id"])


def _freshness(receipts, common, generated):
    market = [row for row in receipts if row["required"] and row["freshness_role"] == "market_observation"]
    stale = sorted(row["source_id"] for row in market if row["freshness_state"] == "stale")
    unknown = sorted(row["source_id"] for row in market if row["freshness_state"] == "unknown")
    degraded = sorted(row["source_id"] for row in market if row["freshness_state"] == "degraded" or row["as_of"] < common)
    oldest = min(owner._v2_timestamp(row["observed_at"]) for row in market)
    return {
        "state": "stale" if stale else "unknown" if unknown else "degraded" if degraded else "fresh",
        "common_as_of": common, "oldest_required_source_at": oldest.isoformat().replace("+00:00", "Z"),
        "evaluated_at": generated, "stale_source_ids": stale, "degraded_source_ids": degraded,
        "unknown_source_ids": unknown, "future_source_ids": [],
    }


def _conflict(key, klass, left, right, refs, en, zh):
    return {
        "conflict_id": "conflict:xlk:" + key, "class": klass, "status": "open",
        "left_ref": left, "right_ref": right, "summary_en": en, "summary_zh": zh,
        "why_en": "Separate owner horizons, scopes and coverage remain visible; no fused score or decision authority.",
        "why_zh": "分别保留负责方周期、范围与覆盖信息，不生成融合评分或决策权限。",
        "source_refs": sorted(set(refs)),
    }


def _headline(sector, children, participation):
    semis = next((row for row in children if row["native_key"] == "semiconductors"), None)
    if (sector.get("split_view") is True and _native_object(sector, "conviction").get("label_en") == "Cautious"
        and _native_object(sector, "rotation").get("state") == "MONEY ROTATING IN"
        and semis is not None and semis["class"] == "entry_now" and semis["regime_state"] == "EXTENDED"
        and participation["value_pct"] is not None and participation["value_pct"] < 50):
        return {
            "state": "selective_leadership",
            "summary_en": "Technology has a constructive fast tape but a cautious slow clock. Semiconductor timing has refreshed while the group is extended and participation is narrow.",
            "summary_zh": "科技板块快线偏强，但慢周期谨慎；半导体择时刷新，该组已偏延伸，参与度仍有限。",
            "posture_en": "Selective leadership; this is not broad sector confirmation.",
            "posture_zh": "选择性领涨，并非板块全面确认。",
            "reason_codes": ["OWNER_TIMEFRAME_SPLIT", "OWNER_SCOPE_SPLIT"],
        }
    return {
        "state": "mixed_or_incomplete",
        "summary_en": "Owner records differ by horizon, scope or coverage; preserve the separate source facts.",
        "summary_zh": "负责方记录在周期、范围或覆盖上存在差异，分别保留源事实。",
        "posture_en": "Descriptive context only; unknown combinations carry no inferred action.",
        "posture_zh": "仅作描述性背景；未知组合不推断行动。",
        "reason_codes": ["NO_FROZEN_COPY_RULE"],
    }


def _governance(subject, token, receipts, freshness, quality, generated, code_version, dossier_id, dimensions, owner_cursors):
    ids = {
        "packet": "packet:sector:" + token, "run": "run:sector-federation:sector:" + token,
        "manifest": "authority:sector-dossier:sector:" + token,
    }
    producer = {"service": "sector-federation", "code_version": code_version, "owner": "neural_web"}
    packet = {
        "contract_id": "sector_intelligence_packet.v2", "schema_version": "2.0.0",
        "packet_id": ids["packet"], "packet_version": 1, "producer": producer,
        "generated_at": generated, "knowledge_cutoff": generated, "subject": subject,
        "entity_refs": [subject["node_id"]], "security_refs": ["XLK"], "portfolio_exposure": [],
        "current_fact_refs": [f"{dossier_id}#/dimensions/{row['dimension_id']}" for row in dimensions],
        "material_change_event_refs": [], "upcoming_event_refs": [], "contradictions": [],
        "freshness": {key: freshness[key] for key in ("state", "oldest_required_source_at", "evaluated_at", "stale_source_ids", "unknown_source_ids")},
        "quality": {"state": quality["state"], "completeness": quality["required_completeness"], "point_in_time_safe": False, "warnings": quality["warnings"]},
        "feature_snapshot_refs": [], "prediction_refs": [], "evidence_claim_refs": [], "source_record_refs": [],
        "lobe_run_ref": ids["run"], "authority_manifest_ref": ids["manifest"],
        "authority_caps": {"max_authority": "A1_EXPLAIN", "allowed_actions": ["observe", "explain"], "forbidden_actions": _DENIALS, "llm_may_originate_signals": False},
        "hash_scope": "canonical_payload_excluding_packet_hash",
    }
    packet["packet_hash"] = owner.canonical_json_sha256(packet)
    watermarks = []
    for receipt in receipts:
        static = receipt["freshness_role"] == "static_config"
        cursor = None if static or receipt["state"] != "available" else owner_cursors.get(receipt["source_id"])
        watermarks.append({"input_receipt": receipt, "watermark": cursor, "state": "not_applicable" if static else ("current" if cursor is not None else "unknown")})
    run = {
        "contract_id": "lobe_run.v2", "schema_version": "2.0.0", "run_id": ids["run"],
        "lobe_id": "sector_federation", "producer": producer, "subject": subject,
        "started_at": generated, "finished_at": generated, "knowledge_cutoff": generated,
        "input_hashes": sorted({row["sha256"] for row in receipts if row["sha256"] is not None}),
        "output_artifacts": [{"artifact_ref": ids["packet"], "content_sha256": packet["packet_hash"], "row_count": 1}],
        "source_watermarks": watermarks,
        "warnings": [{"code": "CURRENT_MEMBERSHIP_NOT_PIT", "source_id": "site-subsector-confluence", "detail": "Current membership is descriptive, not PIT proof.", "retryable": False}],
        "failures": [], "status": "degraded", "completeness": quality["required_completeness"],
        "model_versions": [], "authority_manifest_ref": ids["manifest"],
    }
    manifest = {
        "contract_id": "authority_manifest.v2", "schema_version": "2.0.0", "manifest_id": ids["manifest"],
        "artifact_ref": ids["packet"], "artifact_type": "sector_intelligence_packet.v2", "subject": subject,
        "publication_tier": "SHADOW", "max_authority": "A1_EXPLAIN", "allowed_actions": ["observe", "explain"],
        "denied_actions": _DENIALS, "consumers": ["sector_detail"], "issued_by": "neural_web_governance",
        "issued_at": generated, "valid_from": generated, "valid_to": None,
        "expires_at": (owner._v2_timestamp(generated) + timedelta(hours=72)).isoformat().replace("+00:00", "Z"),
        "promotion_evidence_refs": [], "governance_decision_refs": [],
        "kill_switch": {"enabled": False, "owner": "neural_web_governance", "reason": None, "activated_at": None},
        "transaction_from": generated, "transaction_to": None,
    }
    for document in (packet, run, manifest):
        owner.validate_contract(document)
    return {"packet": packet, "lobe_run": run, "authority_manifest": manifest}


def compose_sector_dossier(*, inputs: FederationInputs, sector_id: str, common_as_of: str, generated_at: str, code_version: str) -> dict[str, Any]:
    """Compose supplied qualified owner facts; no input acquisition or output effect."""
    if sector_id != "xlk":
        raise UnsupportedSector("only the exact accepted xlk sector is admitted")
    if not isinstance(inputs, FederationInputs):
        _fail("inputs must be frozen FederationInputs")
    try:
        date.fromisoformat(common_as_of)
        instant = owner._v2_timestamp(generated_at)
        if instant is None or not isinstance(code_version, str) or not code_version:
            _fail("aware supplied generation clock and nonempty code version are required")
        data = _checked_mapping({key: _plain(getattr(inputs, key)) for key in inputs.__dataclass_fields__})
        receipts = data["input_receipts"]
        issues = owner._v2_receipt_issues(receipts, path="$.input_receipts", cutoff=generated_at, common_as_of=common_as_of)
        if issues:
            _fail("; ".join(str(issue) for issue in issues))
        if date.fromisoformat(common_as_of) > instant.date():
            _fail("common date cannot exceed supplied cutoff UTC date")
        if owner._v2_timestamp(data["action_board"]["generated_utc"]) != instant:
            _fail("caller generation instant must equal the selected stamped action-board owner instant")
        sector = next(row for row in data["sector_central"]["sectors"] if row["id"] == "xlk")
        children = _children(data)
        themes = _connected_themes(data, children)
        child_keys = {row["native_key"] for row in children}
        linked_ids = {row["id"] for row in data["theme_crosswalk"]["themes"]
                      if child_keys.intersection(row["subsector_keys"])}
        missing_health = len(linked_ids - {row["theme_id"] for row in themes})
        participation = _participation(sector, common_as_of)
        concentration = _concentration(data["heatmap"])
        receipt_by_id = {row["source_id"]: row for row in receipts}
        central = ("sector_central", "site/sectordata/sector_central.json#/sectors/xlk")  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        confluence = ("subsector_confluence", "site/marketdata/subsector_confluence.json")  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        heat_source = ("sp500_heatmap", "site/marketdata/sp500_heatmap.json#/tiles")  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        conviction, cycle, rotation = (_native_object(sector, k) for k in ("conviction", "cycle", "rotation"))
        source_children = {row["key"]: row for row in data["subsector_confluence"]["subsectors"] if isinstance(row, Mapping) and row.get("sector") == "Technology"}
        semis = source_children.get("semiconductors")
        entry, regime = (_native_object(semis, "entry"), _native_object(semis, "regime")) if semis else ({}, {})
        leadership = data.get("optional_leadership")
        entry_context = data.get("optional_entry_context")
        # Native consumer context is preserved only where its owner field is available.
        contexts = (entry_context or {}).get("theme_context", {})
        entry_reads = [contexts[row["theme_id"]].get("dimensions", {}).get("entry", {}) for row in themes if row["theme_id"] in contexts]
        available_entry = [row for row in entry_reads if row.get("state") not in (None, "UNAVAILABLE")]
        dimensions = [
            _dimension("sector_slow_clock", source=central, as_of=common_as_of, scope="sector", horizon="multi_year_cycle", state=conviction.get("label_en") or "unavailable", value={"conviction_score": conviction.get("score"), "conviction_label": conviction.get("label_en"), "cycle_phase": cycle.get("phase"), "owner_split_view": sector.get("split_view"), "owner_split_copy_en": sector.get("split_copy_en"), "owner_split_copy_zh": sector.get("split_copy_zh")}),
            _dimension("sector_fast_tape", source=central, as_of=common_as_of, scope="sector", horizon="short_term_rotation", state=rotation.get("state") or "unavailable", value={"rotation_state": rotation.get("state"), "owner_score": rotation.get("score"), "owner_plain_en": rotation.get("state_plain_en"), "owner_plain_zh": rotation.get("state_plain_zh")}),
            _dimension("sector_participation", source=central, as_of=common_as_of, scope="sector", horizon="closed_session", state=participation["state"], value={"value_pct": participation["value_pct"], "n_advancing": participation["n_advancing"], "n_declining": participation["n_declining"], "n_total": participation["n_total"], "unit": "percent"}),
            _dimension("sector_concentration", source=heat_source, as_of=receipt_by_id["sp500-heatmap"]["as_of"], scope="sector", horizon="current_heatmap_snapshot", state=concentration["state"], value={"top5_share": concentration["value"], "n_members": concentration["n_members"], "n_missing_sizes": sum(row.get("size") is None for row in data["heatmap"]["tiles"] if isinstance(row, Mapping) and row.get("sector") == "Technology"), "population": "owner Technology heatmap marketcap", "unit": "share"}),
            _dimension("subsector_entry", source=confluence, as_of=receipt_by_id["site-subsector-confluence"]["as_of"], scope="subsector", horizon="entry_timing_vs_regime", state="available" if children else "valid_empty", value={"n_children": len(children), "owner_class": semis.get("class") if semis else None, "entry_tier": entry.get("tier"), "owner_buyable": entry.get("buyable"), "owner_eligible": entry.get("eligible"), "fresh_bars": entry.get("fresh_bars"), "regime_state": regime.get("state"), "owner_regime_side": regime.get("side")}),
            _dimension("closed_session_leadership", source=("subsector_rotation", leadership["source_ref"] if leadership else "site/marketdata/subsector_rotation.json"), as_of=receipt_by_id["site-subsector-rotation"]["as_of"], scope="subsector", horizon="closed_session", state=leadership["state"] if leadership else "unavailable", value={"owner_state": leadership["state"]} if leadership else None),  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
            _dimension("theme_health", source=("theme_state", "site/neuralwebdata/theme_state.json"), as_of=receipt_by_id["site-theme-state"]["as_of"], scope="theme", horizon="owner_theme_horizons", state="available" if themes else ("unavailable" if missing_health else "valid_empty"), value={"n_connected": len(themes), "n_unavailable_health": missing_health, "n_entry_ready": sum(row["entry_ready"] is True for row in themes), "owner_stages": ",".join(sorted({row["stage"] for row in themes}))} if themes or not missing_health else None, coverage="partial" if missing_health else "complete"),  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
            _dimension("group_entry_context", source=("theme_lanes", "site/basketdata/theme_lanes.json"), as_of=receipt_by_id["site-theme-lanes"]["as_of"] or common_as_of, scope="group", horizon="owner_group_entry", state="available" if available_entry else "unavailable", value={"n_available_owner_entries": len(available_entry), "owner_states": ",".join(sorted({row["state"] for row in available_entry}))} if available_entry else None),  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        ]
        assert tuple(row["dimension_id"] for row in dimensions) == _DIMENSION_ORDER
        freshness = _freshness(receipts, common_as_of, generated_at)
        warnings = ["CURRENT_MEMBERSHIP_NOT_PIT: current structural membership does not establish historical availability."]
        if any(row["freshness_role"] == "static_config" and row["observed_at"] is None for row in receipts):
            warnings.append("STATIC_OWNER_CLOCK_UNAVAILABLE: current hash is known, historical availability is not.")
        for name in ("closed_session_leadership", "group_entry_context"):
            if next(row for row in dimensions if row["dimension_id"] == name)["state"] == "unavailable":
                warnings.append("OPTIONAL_DIMENSION_UNAVAILABLE: " + name)
        if missing_health:
            warnings.append("CONNECTED_THEME_HEALTH_UNAVAILABLE: configured relation alone supplies no health fact.")
        if not data.get("owner_watermarks"):
            warnings.append("OWNER_CURSOR_UNAVAILABLE: no cursor is inferred from a date or observation clock.")
        quality = {"state": "degraded", "required_completeness": 1.0, "optional_dimensions_available": int(leadership is not None) + int(bool(available_entry)), "optional_dimensions_total": 2, "point_in_time_safe": False, "warnings": sorted(warnings)}
        subject = {"kind": "sector", "node_id": "sector:xlk", "native_id": "xlk", "source_family": None}
        token = owner.canonical_json_sha256({"subject": subject, "common_as_of": common_as_of, "code_version": code_version, "source_identity": sorted((row["source_id"], row["sha256"]) for row in receipts if row["sha256"] is not None)})[:24]
        dossier_id = "dossier:sector:" + token
        conflicts = []
        if sector.get("split_view") is True:
            conflicts.append(_conflict("slow-vs-fast", "TIMEFRAME_SPLIT", central[1] + "/conviction", central[1] + "/rotation", [central[1]], "The owner reports different slow and fast clocks.", "负责方报告慢周期与快线存在分歧。"))
        for child in children:
            if child["class"] == "entry_now" and child["regime_state"] == "EXTENDED":
                conflicts.append(_conflict(child["native_key"] + "-entry-vs-regime", "TIMEFRAME_SPLIT", child["source_ref"] + "/entry", child["source_ref"] + "/regime", [child["source_ref"]], "Entry timing refreshed while the owner's regime is extended.", "入场择时已刷新，但负责方形势状态偏延伸。"))
            if child["class"] == "entry_now" and participation["value_pct"] is not None and participation["value_pct"] < 50:
                conflicts.append(_conflict("parent-breadth-vs-" + child["native_key"], "SCOPE_SPLIT", participation["source_ref"], child["source_ref"], [participation["source_ref"], child["source_ref"]], "The child entry state differs from narrow parent participation.", "子板块入场状态与母板块较窄参与度存在范围差异。"))
        if freshness["state"] != "fresh":
            conflicts.append(_conflict("required-freshness", "FRESHNESS_SPLIT", central[1], "site/neuralwebdata/theme_state.json", [row["path"] for row in receipts if row["required"] and row["freshness_role"] == "market_observation"], "Required owner sources differ in date or freshness.", "必要负责方来源在日期或新鲜度上存在差异。"))  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
        read = data.get("same_horizon_owner_read")
        if read is not None:
            bound = next(row for row in receipts if read["source_ref"] == row["path"] or read["source_ref"].startswith(row["path"] + "#/"))
            if (read["scope"] == "sector" and read["horizon"] == "multi_year_cycle" and read["as_of"] == common_as_of
                and bound["as_of"] == common_as_of and bound["freshness_state"] == "fresh"
                and conviction.get("label_en") == "Cautious" and read["state"] == "constructive"):
                conflicts.append(_conflict("qualified-same-horizon", "GENUINE_CONTRADICTION", central[1] + "/conviction", read["source_ref"], [central[1], read["source_ref"]], "Qualified owners disagree on the same sector horizon and date.", "符合资格的负责方对相同板块周期与日期存在分歧。"))
        governance = _governance(subject, token, receipts, freshness, quality, generated_at, code_version, dossier_id, dimensions, data.get("owner_watermarks") or {})
        doc = {
            "contract_id": "sector_dossier_read_model.v2", "schema_version": "2.0.0",
            "dossier_id": dossier_id, "dossier_version": 1, "generated_at": generated_at,
            "knowledge_cutoff": generated_at, "common_as_of": common_as_of,
            "identity": {"subject": subject, "name_en": sector.get("name"), "name_zh": sector.get("name_zh") or "", "representation": "spdr_sector_etf", "page_href": "sectors/XLK.html", "source_refs": [central[1]],
                         "tradable_binding": {"applicability": "applicable", "value": "XLK", "reason": None, "source_refs": [central[1]]},
                         "benchmark_binding": {"applicability": "unavailable", "value": None, "reason": "OWNER_BINDING_UNAVAILABLE", "source_refs": ["site/sectordata/sector_central.json"]}},  # ci-trigger-closure: data — supplied reference identity or output data; never opened here
            "headline": _headline(sector, children, participation), "dimensions": dimensions,
            "material_changes": [], "children": children, "connected_themes": themes,
            "participation": participation, "concentration": concentration,
            "conflicts": sorted(conflicts, key=lambda row: row["conflict_id"]),
            "watch_conditions": [{"condition_id": "watch:xlk:owner-refresh", "state": "open", "label_en": "Owner refresh", "label_zh": "负责方刷新", "condition_en": "Observe the next qualified owner refresh without inferring a trade.", "condition_zh": "观察下一次符合资格的负责方刷新，不推断交易。", "source_refs": [central[1]], "authority": "observation_only"}],
            "freshness": freshness, "quality": quality, "input_receipts": receipts,
            "governance": governance, "authority_caps": copy.deepcopy(_CAPS),
            "hash_scope": "canonical_payload_excluding_dossier_hash",
        }
        doc["dossier_hash"] = owner.canonical_json_sha256(doc)
        owner.validate_contract(doc)
        return doc
    except FederationError:
        raise
    except (owner.ContractError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise FederationError("owner facts or v2 contract binding refused: " + str(exc)) from exc
