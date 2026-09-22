"""Shared presentation adapter for Mastermind Theme Intelligence.

Lane E owns presentation only.  This module consumes the additive Lane A
``theme_intelligence.consumer.v1`` row and optional Lane D
``mastermind.entry_context.v1`` records.  It never composes ThemeState, ranks a
theme or instrument, infers a trade, or widens an owner's capability ceiling.
The JavaScript renderer implements the same bounded adapter for client-rendered
surfaces.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

COMPONENT_VERSION = "theme-opportunity-card.presentation.v5"
OWNER_CONTRACT_SCHEMA = "theme_intelligence.consumer.v1"
ENTRY_CONTEXT_SCHEMA = "mastermind.entry_context.v1"
AXES = ("leadership", "thesis", "crowding", "entry", "health")
AXIS_LABELS = {
    "leadership": ("Leadership", "领导力"),
    "thesis": ("Economic thesis", "经济论点"),
    "crowding": ("Crowding", "拥挤度"),
    "entry": ("Theme-level entry", "主题层入场"),
    "health": ("Evidence health", "证据健康"),
}
TONES = {"neutral", "info", "up", "warn", "down", "unknown"}
ROUTES = {
    "tracker": "state_of_themes.html",
    "foresight": "foresight.html",
    "radar": "radar.html",
    "sector": "sector_central.html",
}
CLOCKS = ("observation", "availability", "computation", "publication")
OWNER_AUTHORITY_TRUE = ("is_context_only", "display_only", "not_a_signal")
OWNER_AUTHORITY_FALSE = ("may_rank", "may_gate", "may_size", "may_escalate", "may_trade")
EVIDENCE_RECORD_KEYS = {
    "ref", "artifact", "source_family", "evidence_family", "source_record_id",
    "observation_id", "parent_identity", "observation_session", "input_hash",
    "source_input_hash", "observed_at", "available_at",
}
ENTRY_QUALIFIED_STATES = {
    "QUALIFIED",
    "QUALIFIED_PENDING_CONFIRMATION",
    "QUALIFIED_PENDING_CONFIRMATION_EXTENDED",
    "QUALIFIED_GROUP_EXTENDED",
}
DEGRADED_HEALTH_STATES = {
    "UNAVAILABLE", "STALE", "ERROR", "FAILED", "DARK_OR_DISCONNECTED", "BROKEN",
}

# Copy may explain owner state, but it may not replace owner state or smuggle
# ranking/trading authority into the component.
DISPLAY_FORBIDDEN_KEYS = {
    "schema", "state", "reason_code", "reason_codes", "source_records",
    "clocks", "watermarks", "bar_status", "authority", "permissions",
    "contract_version", "display_state", "rank", "quality_score",
    "confidence_pct", "confidence_percentage", "buyable", "price_target",
    *OWNER_AUTHORITY_FALSE,
}

ENTRY_PRESENTATION: dict[str, dict[str, str]] = {
    "QUALIFIED": {
        "label_en": "Qualified individual setup",
        "label_zh": "合格的个股形态",
        "reason_en": "The current member gate and owner stock setup agree.",
        "reason_zh": "当前成员门槛与所有者个股形态一致。",
        "tone": "up",
        "cta_en": "Open qualified setup",
        "cta_zh": "打开合格形态",
    },
    "QUALIFIED_PENDING_CONFIRMATION": {
        "label_en": "Qualified; confirmation pending",
        "label_zh": "已合格；等待确认",
        "reason_en": "The setup is current, but the owner still marks confirmation pending.",
        "reason_zh": "形态当前有效，但所有者仍标记为等待确认。",
        "tone": "info",
        "cta_en": "Open qualified setup",
        "cta_zh": "打开合格形态",
    },
    "QUALIFIED_PENDING_CONFIRMATION_EXTENDED": {
        "label_en": "Qualified; confirmation pending, group extended",
        "label_zh": "已合格；等待确认，群组已延伸",
        "reason_en": "The individual setup is current; the parent group is extended, so do not treat the group as fresh entry permission.",
        "reason_zh": "个股形态当前有效；母群组已延伸，不应把群组状态当作新的入场许可。",
        "tone": "warn",
        "cta_en": "Open qualified setup",
        "cta_zh": "打开合格形态",
    },
    "QUALIFIED_GROUP_EXTENDED": {
        "label_en": "Qualified individual setup; group extended",
        "label_zh": "个股形态合格；群组已延伸",
        "reason_en": "The stock setup is qualified independently of the extended parent group.",
        "reason_zh": "个股形态独立合格，母群组则已延伸。",
        "tone": "warn",
        "cta_en": "Open qualified setup",
        "cta_zh": "打开合格形态",
    },
    "QUALIFIED_GROUP_HEADWIND": {
        "label_en": "Individual evidence present; group headwind",
        "label_zh": "个股证据存在；群组有逆风",
        "reason_en": "Review the setup, but do not present it as a qualified entry while the owner reports a group headwind.",
        "reason_zh": "可查看该形态，但所有者报告群组逆风时不得将其展示为合格入场。",
        "tone": "warn",
        "cta_en": "Review setup and headwind",
        "cta_zh": "查看形态与逆风",
    },
    "EXPIRED": {
        "label_en": "Setup expired",
        "label_zh": "形态已过期",
        "reason_en": "The owner no longer considers this a fresh entry.",
        "reason_zh": "所有者不再将其视为新鲜入场。",
        "tone": "down",
        "cta_en": "View expired context",
        "cta_zh": "查看已过期背景",
    },
    "DESCRIPTIVE_ONLY_SETUP_STALE": {
        "label_en": "Stock setup is stale",
        "label_zh": "个股形态已陈旧",
        "reason_en": "The record can be inspected, but it is not current entry permission.",
        "reason_zh": "可以查看记录，但它不是当前入场许可。",
        "tone": "warn",
        "cta_en": "View stale context",
        "cta_zh": "查看陈旧背景",
    },
    "DESCRIPTIVE_ONLY_SETUP_UNAVAILABLE": {
        "label_en": "No current stock setup record",
        "label_zh": "没有当前个股形态记录",
        "reason_en": "Absence is scoped to the named owner snapshot, not the whole market.",
        "reason_zh": "缺失仅限于指定所有者快照，并非全市场缺失。",
        "tone": "unknown",
        "cta_en": "View instrument context",
        "cta_zh": "查看标的背景",
    },
    "DESCRIPTIVE_ONLY_MEMBER_INELIGIBLE": {
        "label_en": "Member is not currently entry-eligible",
        "label_zh": "成员当前不具备入场资格",
        "reason_en": "Parent-group strength does not grant this member buyability.",
        "reason_zh": "母群组强势不会赋予该成员可买性。",
        "tone": "neutral",
        "cta_en": "View instrument context",
        "cta_zh": "查看标的背景",
    },
    "DESCRIPTIVE_ONLY_SETUP_INELIGIBLE": {
        "label_en": "Stock setup is not qualified",
        "label_zh": "个股形态未合格",
        "reason_en": "The owner setup record does not pass the current stock gate.",
        "reason_zh": "所有者形态记录未通过当前个股门槛。",
        "tone": "neutral",
        "cta_en": "View instrument context",
        "cta_zh": "查看标的背景",
    },
    "DESCRIPTIVE_ONLY_PROXY": {
        "label_en": "Proxy exposure only",
        "label_zh": "仅为代理敞口",
        "reason_en": "A proxy relationship cannot be presented as a direct qualified stock setup.",
        "reason_zh": "代理关系不得展示为直接合格的个股形态。",
        "tone": "unknown",
        "cta_en": "View proxy context",
        "cta_zh": "查看代理背景",
    },
    "DESCRIPTIVE_ONLY_RELATIONSHIP_UNKNOWN": {
        "label_en": "Relationship unresolved",
        "label_zh": "关系尚未解析",
        "reason_en": "The instrument relationship is unknown, so entry qualification is withheld.",
        "reason_zh": "标的关系未知，因此不展示入场资格。",
        "tone": "unknown",
        "cta_en": "View instrument context",
        "cta_zh": "查看标的背景",
    },
}


class CardPresentationError(ValueError):
    """Raised when presentation input would blur source truth or authority."""


def _mapping(parent: Mapping[str, Any], key: str, *, path: str | None = None) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, Mapping):
        raise CardPresentationError(f"{path or key} must be a mapping")
    return dict(value)


def _text(parent: Mapping[str, Any], key: str, *, path: str | None = None) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CardPresentationError(f"{path or key} must be non-empty text")
    return value


def _nullable_text(parent: Mapping[str, Any], key: str, *, path: str | None = None) -> str | None:
    if key not in parent:
        raise CardPresentationError(f"{path or key} must be explicitly present")
    value = parent[key]
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise CardPresentationError(f"{path or key} must be null or non-empty text")
    return value


def _text_list(value: Any, *, path: str) -> list[str]:
    if not isinstance(value, list):
        raise CardPresentationError(f"{path} must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise CardPresentationError(f"{path} must contain only non-empty text")
    return list(value)


def _evidence_records(value: Any, *, path: str) -> list[dict[str, Any]]:
    """Validate Lane A provenance records without flattening owner identity."""
    if not isinstance(value, list):
        raise CardPresentationError(f"{path} must be a list")
    records: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_path = f"{path}[{index}]"
        if isinstance(item, str):
            if not item.strip():
                raise CardPresentationError(f"{item_path} must be non-empty text")
            records.append({"ref": item})
            continue
        if not isinstance(item, Mapping):
            raise CardPresentationError(f"{item_path} must be text or a provenance record")
        record = dict(item)
        unknown = set(record) - EVIDENCE_RECORD_KEYS
        if unknown:
            raise CardPresentationError(
                f"{item_path} has unsupported provenance fields: {', '.join(sorted(unknown))}"
            )
        if not record:
            raise CardPresentationError(f"{item_path} must not be empty")
        for key, raw in record.items():
            if raw is not None and (not isinstance(raw, str) or not raw.strip()):
                raise CardPresentationError(f"{item_path}.{key} must be null or non-empty text")
        if not any(raw is not None for raw in record.values()):
            raise CardPresentationError(f"{item_path} must carry at least one owner identity field")
        records.append(deepcopy(record))
    return records


def _evidence_record_label(record: Mapping[str, Any]) -> str:
    for key in ("ref", "artifact"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    ordered = (
        ("family", record.get("source_family") or record.get("evidence_family")),
        ("parent", record.get("parent_identity")),
        ("session", record.get("observation_session")),
        ("input", record.get("input_hash") or record.get("source_input_hash")),
        ("observation", record.get("observation_id")),
        ("record", record.get("source_record_id")),
    )
    label = " · ".join(f"{key}={value}" for key, value in ordered if value)
    if not label:
        raise CardPresentationError("provenance record has no displayable owner identity")
    return label


def _evidence_record_labels(records: Sequence[Mapping[str, Any]]) -> list[str]:
    return [_evidence_record_label(record) for record in records]


def _validate_evidence_identity(raw: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    identity = dict(raw)
    if set(identity) != {"available", "reason_code", "records"}:
        raise CardPresentationError(
            f"{path} must contain available, reason_code and records"
        )
    if not isinstance(identity["available"], bool):
        raise CardPresentationError(f"{path}.available must be true or false")
    reason = identity["reason_code"]
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise CardPresentationError(f"{path}.reason_code must be null or non-empty text")
    records = _evidence_records(identity["records"], path=f"{path}.records")
    if identity["available"] and not records:
        raise CardPresentationError(f"{path}.available cannot be true without owner records")
    if not identity["available"] and not reason:
        # Additive compatibility with older producer rows: absence stays explicit
        # but no synthetic owner reason is minted.
        reason = None
    return {"available": identity["available"], "reason_code": reason, "records": records}


def _validate_dimension_clock_map(raw: Any, *, path: str) -> dict[str, dict[str, str | None]]:
    """Accept Lane A scalar clocks and preserved Lane D {value, reason} leaves."""
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    clocks = dict(raw)
    if set(clocks) != set(CLOCKS):
        raise CardPresentationError(
            f"{path} must keep observation/availability/computation/publication separate"
        )
    clean: dict[str, dict[str, str | None]] = {}
    for key in CLOCKS:
        raw_leaf = clocks[key]
        if isinstance(raw_leaf, Mapping):
            leaf = dict(raw_leaf)
            if set(leaf) != {"value", "reason"}:
                raise CardPresentationError(f"{path}.{key} must contain value and reason")
            value = leaf["value"]
            reason = leaf["reason"]
        else:
            value = raw_leaf
            reason = None
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise CardPresentationError(f"{path}.{key}.value must be null or non-empty text")
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise CardPresentationError(f"{path}.{key}.reason must be null or non-empty text")
        clean[key] = {"value": value, "reason": reason}
    return clean


def _clock_values(details: Mapping[str, Mapping[str, Any]]) -> dict[str, str | None]:
    return {key: details[key].get("value") for key in CLOCKS}


def _clock_reasons(details: Mapping[str, Mapping[str, Any]]) -> dict[str, str | None]:
    return {key: details[key].get("reason") for key in CLOCKS}


def _tone(value: Any, *, path: str) -> str:
    if value not in TONES:
        raise CardPresentationError(f"{path} has unsupported presentation tone {value!r}")
    return str(value)


def _route(value: Any, *, path: str, expected_page: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CardPresentationError(f"{path} must be a non-empty safe relative route")
    decoded_value = unquote(value)
    parsed = urlsplit(decoded_value)
    decoded_path = parsed.path
    lowered = decoded_value.lower()
    if (
        parsed.scheme
        or parsed.netloc
        or decoded_value.startswith(("/", "//"))
        or lowered.startswith(("javascript:", "data:"))
        or "\\" in decoded_path
        or any(ord(character) < 32 for character in decoded_value)
        or any(part == ".." for part in decoded_path.split("/"))
    ):
        raise CardPresentationError(f"{path} must be a safe relative route")
    if expected_page and decoded_path != expected_page:
        raise CardPresentationError(f"{path} must preserve {expected_page}")
    return value


def _walk_display_copy(value: Any, path: str = "display") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in DISPLAY_FORBIDDEN_KEYS:
                raise CardPresentationError(f"{path}.{key} is owner-controlled, not presentation copy")
            _walk_display_copy(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _walk_display_copy(nested, f"{path}[{index}]")


def _validate_authority(authority: Mapping[str, Any], *, path: str, include_true: bool) -> dict[str, Any]:
    result = dict(authority)
    expected = set(OWNER_AUTHORITY_FALSE)
    if include_true:
        expected.update(OWNER_AUTHORITY_TRUE)
    if set(result) != expected:
        raise CardPresentationError(f"{path} must use the complete closed authority field set")
    if include_true:
        for key in OWNER_AUTHORITY_TRUE:
            if result.get(key) is not True:
                raise CardPresentationError(f"{path}.{key} must remain true")
    for key in OWNER_AUTHORITY_FALSE:
        if result.get(key) is not False:
            raise CardPresentationError(f"{path}.{key} must remain false")
    return result


def _validate_clock_map(raw: Any, *, path: str) -> dict[str, str | None]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    clocks = dict(raw)
    if set(clocks) != set(CLOCKS):
        raise CardPresentationError(f"{path} must keep observation/availability/computation/publication separate")
    for key in CLOCKS:
        value = clocks[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise CardPresentationError(f"{path}.{key} must be null or non-empty text")
    return clocks


def _validate_bar_status(raw: Any, *, path: str) -> dict[str, bool | None]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    status = dict(raw)
    if set(status) != {"closed", "provisional"}:
        raise CardPresentationError(f"{path} must contain closed and provisional")
    for key, value in status.items():
        if value is not None and not isinstance(value, bool):
            raise CardPresentationError(f"{path}.{key} must be true, false, or null")
    return status


def _owner_details(dimension: Mapping[str, Any], *, path: str) -> dict[str, Any]:
    """Preserve Lane A's flat descriptive label/value/band without reinterpreting it."""
    details: dict[str, Any] = {}
    for key in ("label", "value", "band"):
        if key not in dimension:
            continue
        value = dimension[key]
        if isinstance(value, (Mapping, list, tuple, set)):
            raise CardPresentationError(f"{path}.{key} must be a scalar or null")
        if key in {"label", "band"} and value is not None:
            if not isinstance(value, str) or not value.strip():
                raise CardPresentationError(f"{path}.{key} must be null or non-empty text")
        details[key] = deepcopy(value)
    return details


def _validate_entry_clock_leaf(raw: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    leaf = dict(raw)
    if set(leaf) != {"value", "reason"}:
        raise CardPresentationError(f"{path} must contain value and reason")
    value = leaf["value"]
    if isinstance(value, (Mapping, list, tuple, set)):
        raise CardPresentationError(f"{path}.value must be a scalar or null")
    reason = leaf["reason"]
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise CardPresentationError(f"{path}.reason must be null or non-empty text")
    return deepcopy(leaf)


def _validate_entry_clocks(raw: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    clocks = dict(raw)
    required = {"stock_setup", "group", "live_entry_radar"}
    if not required.issubset(clocks):
        missing = ", ".join(sorted(required - set(clocks)))
        raise CardPresentationError(f"{path} is missing required owner clock sets: {missing}")
    clean: dict[str, Any] = {}
    for owner, raw_clock_set in clocks.items():
        if not isinstance(owner, str) or not owner.strip():
            raise CardPresentationError(f"{path} owner keys must be non-empty text")
        if not isinstance(raw_clock_set, Mapping):
            raise CardPresentationError(f"{path}.{owner} must be a mapping")
        clock_set = dict(raw_clock_set)
        if set(clock_set) != set(CLOCKS):
            raise CardPresentationError(
                f"{path}.{owner} must keep observation/availability/computation/publication separate"
            )
        clean[owner] = {
            key: _validate_entry_clock_leaf(
                clock_set[key], path=f"{path}.{owner}.{key}"
            )
            for key in CLOCKS
        }
    return clean


def _validate_entry_lineage(raw: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError(f"{path} must be a mapping")
    lineage = dict(raw)
    expected = {
        "state", "source_revision", "correction_of", "supersedes",
        "source_content_sha256", "reason",
    }
    if set(lineage) != expected:
        raise CardPresentationError(f"{path} must use the exact Lane D lineage fields")
    _text(lineage, "state", path=f"{path}.state")
    revision = lineage["source_revision"]
    if revision is not None and isinstance(revision, (Mapping, list, tuple, set)):
        raise CardPresentationError(f"{path}.source_revision must be a scalar or null")
    for key in ("correction_of", "supersedes", "source_content_sha256", "reason"):
        value = lineage[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise CardPresentationError(f"{path}.{key} must be null or non-empty text")
    return deepcopy(lineage)


def _validate_owner_context(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError("theme_context must be a mapping")
    owner = deepcopy(dict(raw))
    if owner.get("schema") != OWNER_CONTRACT_SCHEMA:
        raise CardPresentationError(f"theme_context.schema must be {OWNER_CONTRACT_SCHEMA}")

    identity = _mapping(owner, "identity", path="theme_context.identity")
    theme_id = _text(identity, "theme_id", path="theme_context.identity.theme_id")
    if not all(character.isalnum() or character in "_-" for character in theme_id):
        raise CardPresentationError("theme_context.identity.theme_id contains unsafe characters")
    for key in ("relationship_kind", "basket_id", "market", "horizon"):
        _nullable_text(identity, key, path=f"theme_context.identity.{key}")

    dimensions = _mapping(owner, "dimensions", path="theme_context.dimensions")
    if set(dimensions) != set(AXES):
        raise CardPresentationError("theme_context.dimensions must contain exactly the five Lane A dimensions")
    for name in AXES:
        dimension = _mapping(dimensions, name, path=f"theme_context.dimensions.{name}")
        _text(dimension, "state", path=f"theme_context.dimensions.{name}.state")
        if "reason_code" in dimension and dimension["reason_code"] is not None:
            _text(dimension, "reason_code", path=f"theme_context.dimensions.{name}.reason_code")
        if "reason_codes" in dimension:
            _text_list(dimension["reason_codes"], path=f"theme_context.dimensions.{name}.reason_codes")
        if "source_records" in dimension:
            dimension["source_records"] = _evidence_records(
                dimension["source_records"],
                path=f"theme_context.dimensions.{name}.source_records",
            )
        if "clocks" in dimension:
            dimension["clocks"] = _validate_dimension_clock_map(
                dimension["clocks"], path=f"theme_context.dimensions.{name}.clocks"
            )
        if "bar_status" in dimension:
            _validate_bar_status(dimension["bar_status"], path=f"theme_context.dimensions.{name}.bar_status")
        for forbidden in OWNER_AUTHORITY_FALSE:
            if forbidden in dimension:
                raise CardPresentationError(
                    f"theme_context.dimensions.{name}.{forbidden} is not descriptive owner data"
                )
        dimensions[name] = dimension
    owner["dimensions"] = dimensions

    _mapping(owner, "specialist_context", path="theme_context.specialist_context")
    owner["source_records"] = _evidence_records(
        owner.get("source_records"), path="theme_context.source_records"
    )
    if "evidence_identity" in owner:
        owner["evidence_identity"] = _validate_evidence_identity(
            owner["evidence_identity"], path="theme_context.evidence_identity"
        )
    else:
        owner["evidence_identity"] = {
            "available": False, "reason_code": None, "records": []
        }
    _text_list(
        owner.get("independent_evidence_families"),
        path="theme_context.independent_evidence_families",
    )
    _validate_clock_map(owner.get("clocks"), path="theme_context.clocks")
    watermarks = _mapping(owner, "watermarks", path="theme_context.watermarks")
    if "snapshot" not in watermarks or "inputs" not in watermarks:
        raise CardPresentationError("theme_context.watermarks must contain snapshot and inputs")
    if watermarks["snapshot"] is not None and not isinstance(watermarks["snapshot"], str):
        raise CardPresentationError("theme_context.watermarks.snapshot must be text or null")
    if not isinstance(watermarks["inputs"], Mapping):
        raise CardPresentationError("theme_context.watermarks.inputs must be a mapping")
    for key, value in watermarks["inputs"].items():
        if not isinstance(key, str) or not key.strip():
            raise CardPresentationError("theme_context.watermarks.inputs keys must be text")
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise CardPresentationError("theme_context.watermarks.inputs values must be text or null")
    _validate_bar_status(owner.get("bar_status"), path="theme_context.bar_status")
    lineage = _mapping(owner, "correction_lineage", path="theme_context.correction_lineage")
    for key in ("supersedes", "first_observed", "first_displayed"):
        _nullable_text(lineage, key, path=f"theme_context.correction_lineage.{key}")
    _validate_authority(
        _mapping(owner, "authority", path="theme_context.authority"),
        path="theme_context.authority",
        include_true=True,
    )
    return owner


def _validate_display(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError("display must be a mapping")
    display = deepcopy(dict(raw))
    _walk_display_copy(display)
    theme = _mapping(display, "theme", path="display.theme")
    _text(theme, "name_en", path="display.theme.name_en")
    _text(theme, "name_zh", path="display.theme.name_zh")
    surface = _mapping(display, "surface", path="display.surface")
    _text(surface, "source_lens_en", path="display.surface.source_lens_en")
    _text(surface, "source_lens_zh", path="display.surface.source_lens_zh")
    _route(surface.get("current_route"), path="display.surface.current_route")
    summary = _mapping(display, "summary", path="display.summary")
    for key in (
        "what_changed_en", "what_changed_zh", "why_matters_en", "why_matters_zh",
        "opportunity_en", "opportunity_zh", "risk_en", "risk_zh",
        "disagreement_en", "disagreement_zh",
    ):
        _text(summary, key, path=f"display.summary.{key}")
    dimensions = _mapping(display, "dimensions", path="display.dimensions")
    if set(dimensions) != set(AXES):
        raise CardPresentationError("display.dimensions must explain exactly the five owner dimensions")
    for name in AXES:
        block = _mapping(dimensions, name, path=f"display.dimensions.{name}")
        for key in ("label_en", "label_zh", "reason_en", "reason_zh"):
            _text(block, key, path=f"display.dimensions.{name}.{key}")
        _tone(block.get("tone"), path=f"display.dimensions.{name}.tone")
    names = display.get("names")
    if not isinstance(names, list):
        raise CardPresentationError("display.names must be a list")
    for index, raw_name in enumerate(names):
        if not isinstance(raw_name, Mapping):
            raise CardPresentationError(f"display.names[{index}] must be a mapping")
        name = dict(raw_name)
        for key in (
            "instrument_id", "symbol", "name_en", "name_zh",
            "relationship_kind", "membership_basis", "membership_as_of",
        ):
            _text(name, key, path=f"display.names[{index}].{key}")
    routes = _mapping(display, "routes", path="display.routes")
    if set(routes) != set(ROUTES):
        raise CardPresentationError("display.routes must contain tracker, foresight, radar and sector")
    for key, page in ROUTES.items():
        _route(routes[key], path=f"display.routes.{key}", expected_page=page)
    return display


def _validate_health_copy(owner_dimensions: Mapping[str, Any], display_dimensions: Mapping[str, Any]) -> None:
    """Prevent source failure from being silently translated into a quiet read."""
    health = dict(owner_dimensions["health"])
    health_copy = dict(display_dimensions["health"])
    if str(health.get("state") or "").upper() not in DEGRADED_HEALTH_STATES:
        return
    if health_copy.get("tone") not in {"warn", "down", "unknown"}:
        raise CardPresentationError(
            "display.dimensions.health must visibly disclose degraded source health"
        )
    prose = " ".join(
        str(health_copy.get(key) or "").lower()
        for key in ("label_en", "label_zh", "reason_en", "reason_zh")
    )
    if any(term in prose for term in ("quiet", "nothing notable", "平静", "暂无值得关注")):
        raise CardPresentationError(
            "source failure cannot be presented as quiet"
        )


def _entry_setup_from_owner(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CardPresentationError("entry_context must be a mapping")
    entry = deepcopy(dict(raw))
    if entry.get("schema") != ENTRY_CONTEXT_SCHEMA:
        raise CardPresentationError(f"entry_context.schema must be {ENTRY_CONTEXT_SCHEMA}")
    if entry.get("context_only") is not True:
        raise CardPresentationError("entry_context.context_only must remain true")
    _validate_authority(
        _mapping(entry, "authority", path="entry_context.authority"),
        path="entry_context.authority",
        include_true=False,
    )
    permissions = _mapping(entry, "permissions", path="entry_context.permissions")
    if set(permissions) != {"may_describe", "may_link", *OWNER_AUTHORITY_FALSE}:
        raise CardPresentationError("entry_context.permissions must use the complete closed field set")
    if permissions.get("may_describe") is not True or permissions.get("may_link") is not True:
        raise CardPresentationError("entry_context may_describe and may_link must remain true")
    for key in OWNER_AUTHORITY_FALSE:
        if permissions.get(key) is not False:
            raise CardPresentationError(f"entry_context.permissions.{key} must remain false")

    instrument = _mapping(entry, "instrument", path="entry_context.instrument")
    instrument_id = _text(instrument, "id", path="entry_context.instrument.id")
    relationship = _mapping(entry, "relationship", path="entry_context.relationship")
    qualification = _mapping(entry, "qualification", path="entry_context.qualification")
    stock_setup = _mapping(entry, "stock_setup", path="entry_context.stock_setup")
    expiry = _mapping(entry, "expiry", path="entry_context.expiry")
    routing = _mapping(entry, "routing", path="entry_context.routing")
    routes = _mapping(entry, "routes", path="entry_context.routes")
    group_context = _mapping(entry, "group_context", path="entry_context.group_context")
    confirmation = _mapping(entry, "confirmation", path="entry_context.confirmation")
    levels = _mapping(entry, "levels", path="entry_context.levels")
    href = _route(routes.get("instrument"), path="entry_context.routes.instrument")
    group_href = _route(routes.get("group"), path="entry_context.routes.group")
    state = _text(routing, "state", path="entry_context.routing.state")
    for key in ("may_navigate", "may_present_as_qualified_setup", "may_present_as_headwind_warning"):
        if not isinstance(routing.get(key), bool):
            raise CardPresentationError(f"entry_context.routing.{key} must be explicit true/false")
    if routing.get("rank_effect") != "NONE" or routing.get("size_effect") != "NONE":
        raise CardPresentationError("entry_context routing cannot affect rank or size")

    qualified = routing["may_present_as_qualified_setup"]
    headwind_warning = routing["may_present_as_headwind_warning"]
    may_navigate = routing["may_navigate"]
    if qualified:
        if state not in ENTRY_QUALIFIED_STATES:
            raise CardPresentationError("qualified entry uses an unsupported routing state")
        if instrument.get("kind") != "DIRECT_INSTRUMENT":
            raise CardPresentationError("qualified entry requires DIRECT_INSTRUMENT")
        if relationship.get("kind") != "DIRECT_MEMBER":
            raise CardPresentationError("qualified entry requires DIRECT_MEMBER")
        if qualification.get("member_gate") != "QUALIFIED":
            raise CardPresentationError("qualified entry requires qualified member gate")
        if qualification.get("stock_setup") != "QUALIFIED":
            raise CardPresentationError("qualified entry requires qualified stock setup")
        if stock_setup.get("availability") != "AVAILABLE":
            raise CardPresentationError("qualified entry requires available stock setup")
        if expiry.get("state") != "ACTIVE":
            raise CardPresentationError("qualified entry requires active expiry state")
    if headwind_warning and state != "QUALIFIED_GROUP_HEADWIND":
        raise CardPresentationError("headwind warning must use QUALIFIED_GROUP_HEADWIND")
    if headwind_warning and qualified:
        raise CardPresentationError("headwind warning cannot be presented as a qualified setup")

    presentation = ENTRY_PRESENTATION.get(state, {
        "label_en": "Individual entry context",
        "label_zh": "个股入场背景",
        "reason_en": "The owner supplied entry context; inspect the exact routing state and receipt.",
        "reason_zh": "所有者提供了入场背景；请查看精确路由状态与依据。",
        "tone": "unknown",
        "cta_en": "View instrument context",
        "cta_zh": "查看标的背景",
    })
    return {
        "instrument_id": instrument_id,
        "instrument_kind": instrument.get("kind"),
        "relationship_kind": relationship.get("kind"),
        "group_id": relationship.get("group_id"),
        "group_label": relationship.get("group_label"),
        "routing_state": state,
        "qualified": qualified,
        "headwind_warning": headwind_warning,
        "may_navigate": may_navigate,
        "href": href if may_navigate else None,
        "group_href": group_href if may_navigate else None,
        "record_ref": stock_setup.get("source_ref"),
        "record_id": stock_setup.get("source_setup_id"),
        "label_en": presentation["label_en"],
        "label_zh": presentation["label_zh"],
        "reason_en": presentation["reason_en"],
        "reason_zh": presentation["reason_zh"],
        "tone": presentation["tone"],
        "cta_en": presentation["cta_en"],
        "cta_zh": presentation["cta_zh"],
        "confirmation_state": confirmation.get("state"),
        "group_confirmation_state": confirmation.get("group_state"),
        "group_extended": bool(group_context.get("extended")),
        "group_headwind": bool(group_context.get("headwind")),
        "availability": stock_setup.get("availability"),
        "expiry_state": expiry.get("state"),
        "levels": levels,
        "clocks": _validate_entry_clocks(
            entry.get("clocks"), path="entry_context.clocks"
        ),
        "lineage": _validate_entry_lineage(
            entry.get("lineage"), path="entry_context.lineage"
        ),
    }


def compose_from_owner_context(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Build the shared card from exact Lane A and optional Lane D owner rows."""
    if not isinstance(raw, Mapping):
        raise CardPresentationError("owner envelope must be a mapping")
    envelope = dict(raw)
    if not isinstance(envelope.get("fixture"), bool):
        raise CardPresentationError("fixture must be explicit true/false")
    source_record_ref = _text(
        envelope, "theme_context_ref", path="theme_context_ref"
    )
    owner = _validate_owner_context(envelope.get("theme_context"))
    display = _validate_display(envelope.get("display"))

    owner_dimensions = dict(owner["dimensions"])
    display_dimensions = dict(display["dimensions"])
    _validate_health_copy(owner_dimensions, display_dimensions)
    top_clocks = _validate_clock_map(owner["clocks"], path="theme_context.clocks")
    top_bar_status = _validate_bar_status(owner["bar_status"], path="theme_context.bar_status")
    axes: dict[str, dict[str, Any]] = {}
    for name in AXES:
        dimension = dict(owner_dimensions[name])
        copy_block = dict(display_dimensions[name])
        reason_codes = list(dimension.get("reason_codes") or [])
        if dimension.get("reason_code"):
            reason_codes.insert(0, dimension["reason_code"])
        # Keep order but remove duplicate owner codes without inventing one.
        reason_codes = list(dict.fromkeys(reason_codes))
        dimension_records = list(dimension.get("source_records") or [])
        clock_details = (
            deepcopy(dimension["clocks"])
            if dimension.get("clocks")
            else {
                key: {"value": top_clocks[key], "reason": None}
                for key in CLOCKS
            }
        )
        axes[name] = {
            **deepcopy(copy_block),
            "state": dimension["state"],
            "owner_details": _owner_details(
                dimension, path=f"theme_context.dimensions.{name}"
            ),
            "reason_codes": reason_codes,
            "source_records": deepcopy(dimension_records),
            "source_refs": _evidence_record_labels(dimension_records),
            "clocks": _clock_values(clock_details),
            "clock_reasons": _clock_reasons(clock_details),
            "watermarks": deepcopy(dimension.get("watermarks") or owner["watermarks"]),
            "bar_status": deepcopy(dimension.get("bar_status") or top_bar_status),
        }

    identity = dict(owner["identity"])
    model = {
        "fixture": envelope["fixture"],
        "source_contract": owner["schema"],
        "source_record_ref": source_record_ref,
        "theme": {**deepcopy(identity), **deepcopy(display["theme"])},
        "surface": deepcopy(display["surface"]),
        "summary": deepcopy(display["summary"]),
        "axes": axes,
        "axis_order": AXES,
        "axis_labels": AXIS_LABELS,
        "specialist_context": deepcopy(owner["specialist_context"]),
        "names": deepcopy(display["names"]),
        "routes": deepcopy(display["routes"]),
        "entry_setups": [
            _entry_setup_from_owner(item)
            for item in (envelope.get("entry_contexts") or [])
        ],
        "receipts": {
            "source_records": _evidence_record_labels(owner["source_records"]),
            "source_record_details": deepcopy(owner["source_records"]),
            "evidence_identity": deepcopy(owner["evidence_identity"]),
            "evidence_identity_refs": _evidence_record_labels(
                owner["evidence_identity"]["records"]
            ),
            "independent_evidence_families": deepcopy(
                owner["independent_evidence_families"]
            ),
            "clocks": deepcopy(top_clocks),
            "watermarks": deepcopy(owner["watermarks"]),
            "bar_status": deepcopy(top_bar_status),
            "correction_lineage": deepcopy(owner["correction_lineage"]),
        },
        "authority": deepcopy(owner["authority"]),
        "component_version": COMPONENT_VERSION,
    }
    return validate_presentation(model)


def validate_presentation(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the sanitized presentation model used by both renderers."""
    if not isinstance(raw, Mapping):
        raise CardPresentationError("card must be a mapping")
    card = deepcopy(dict(raw))
    if not isinstance(card.get("fixture"), bool):
        raise CardPresentationError("fixture must be explicit true/false")
    if card.get("source_contract") != OWNER_CONTRACT_SCHEMA:
        raise CardPresentationError(f"source_contract must be {OWNER_CONTRACT_SCHEMA}")
    _text(card, "source_record_ref")

    theme = _mapping(card, "theme")
    theme_id = _text(theme, "theme_id")
    if not all(character.isalnum() or character in "_-" for character in theme_id):
        raise CardPresentationError("theme.theme_id contains unsafe characters")
    for key in ("name_en", "name_zh"):
        _text(theme, key)
    for key in ("relationship_kind", "basket_id", "market", "horizon"):
        _nullable_text(theme, key)

    surface = _mapping(card, "surface")
    _text(surface, "source_lens_en")
    _text(surface, "source_lens_zh")
    _route(surface.get("current_route"), path="surface.current_route")

    summary = _mapping(card, "summary")
    _walk_display_copy(summary, "summary")
    for key in (
        "what_changed_en", "what_changed_zh", "why_matters_en", "why_matters_zh",
        "opportunity_en", "opportunity_zh", "risk_en", "risk_zh",
        "disagreement_en", "disagreement_zh",
    ):
        _text(summary, key)

    axes = _mapping(card, "axes")
    if set(axes) != set(AXES):
        raise CardPresentationError("axes must contain exactly the five Lane A dimensions")
    for name in AXES:
        axis = _mapping(axes, name, path=f"axes.{name}")
        _text(axis, "state", path=f"axes.{name}.state")
        for key in ("label_en", "label_zh", "reason_en", "reason_zh"):
            _text(axis, key, path=f"axes.{name}.{key}")
        _tone(axis.get("tone"), path=f"axes.{name}.tone")
        owner_details = _mapping(axis, "owner_details", path=f"axes.{name}.owner_details")
        if not set(owner_details).issubset({"label", "value", "band"}):
            raise CardPresentationError(f"axes.{name}.owner_details has unsupported fields")
        _owner_details(owner_details, path=f"axes.{name}.owner_details")
        _text_list(axis.get("reason_codes"), path=f"axes.{name}.reason_codes")
        _evidence_records(axis.get("source_records"), path=f"axes.{name}.source_records")
        _text_list(axis.get("source_refs"), path=f"axes.{name}.source_refs")
        _validate_clock_map(axis.get("clocks"), path=f"axes.{name}.clocks")
        clock_reasons = _mapping(axis, "clock_reasons", path=f"axes.{name}.clock_reasons")
        if set(clock_reasons) != set(CLOCKS):
            raise CardPresentationError(
                f"axes.{name}.clock_reasons must keep observation/availability/computation/publication separate"
            )
        for clock_name in CLOCKS:
            reason = clock_reasons[clock_name]
            if reason is not None and (not isinstance(reason, str) or not reason.strip()):
                raise CardPresentationError(
                    f"axes.{name}.clock_reasons.{clock_name} must be null or non-empty text"
                )
        _validate_bar_status(axis.get("bar_status"), path=f"axes.{name}.bar_status")
        if not isinstance(axis.get("watermarks"), Mapping):
            raise CardPresentationError(f"axes.{name}.watermarks must be a mapping")

    names = card.get("names")
    if not isinstance(names, list):
        raise CardPresentationError("names must be a list")
    for index, raw_name in enumerate(names):
        if not isinstance(raw_name, Mapping):
            raise CardPresentationError(f"names[{index}] must be a mapping")
        for key in (
            "instrument_id", "symbol", "name_en", "name_zh",
            "relationship_kind", "membership_basis", "membership_as_of",
        ):
            _text(raw_name, key, path=f"names[{index}].{key}")

    setups = card.get("entry_setups")
    if not isinstance(setups, list):
        raise CardPresentationError("entry_setups must be a list")
    for index, raw_setup in enumerate(setups):
        if not isinstance(raw_setup, Mapping):
            raise CardPresentationError(f"entry_setups[{index}] must be a mapping")
        setup = dict(raw_setup)
        for key in (
            "instrument_id", "instrument_kind", "relationship_kind",
            "routing_state", "label_en", "label_zh", "reason_en", "reason_zh",
            "tone", "cta_en", "cta_zh",
        ):
            _text(setup, key, path=f"entry_setups[{index}].{key}")
        _tone(setup["tone"], path=f"entry_setups[{index}].tone")
        for key in ("qualified", "headwind_warning", "may_navigate", "group_extended", "group_headwind"):
            if not isinstance(setup.get(key), bool):
                raise CardPresentationError(f"entry_setups[{index}].{key} must be explicit true/false")
        for key in ("href", "group_href", "record_ref", "record_id"):
            if key not in setup:
                raise CardPresentationError(f"entry_setups[{index}].{key} must be explicit")
        expected_qualified = setup["routing_state"] in ENTRY_QUALIFIED_STATES
        if setup["qualified"] is not expected_qualified:
            raise CardPresentationError(
                f"entry_setups[{index}] qualified flag must match the owner routing state"
            )
        expected_headwind = setup["routing_state"] == "QUALIFIED_GROUP_HEADWIND"
        if setup["headwind_warning"] is not expected_headwind:
            raise CardPresentationError(
                f"entry_setups[{index}] headwind warning must match the owner routing state"
            )
        if setup["qualified"]:
            if setup["instrument_kind"] != "DIRECT_INSTRUMENT":
                raise CardPresentationError(
                    f"entry_setups[{index}] qualified setup requires DIRECT_INSTRUMENT"
                )
            if setup["relationship_kind"] != "DIRECT_MEMBER":
                raise CardPresentationError(
                    f"entry_setups[{index}] qualified setup requires DIRECT_MEMBER"
                )
            if setup.get("availability") != "AVAILABLE":
                raise CardPresentationError(
                    f"entry_setups[{index}] qualified setup requires available owner data"
                )
            if setup.get("expiry_state") != "ACTIVE":
                raise CardPresentationError(
                    f"entry_setups[{index}] qualified setup requires active owner expiry"
                )
        if setup["may_navigate"]:
            _route(setup["href"], path=f"entry_setups[{index}].href")
            _route(setup["group_href"], path=f"entry_setups[{index}].group_href")
        elif setup["href"] is not None or setup["group_href"] is not None:
            raise CardPresentationError("non-navigable setup cannot carry routes")
        _validate_entry_clocks(
            setup.get("clocks"), path=f"entry_setups[{index}].clocks"
        )
        _validate_entry_lineage(
            setup.get("lineage"), path=f"entry_setups[{index}].lineage"
        )

    routes = _mapping(card, "routes")
    if set(routes) != set(ROUTES):
        raise CardPresentationError("routes must contain tracker, foresight, radar and sector")
    for key, page in ROUTES.items():
        _route(routes[key], path=f"routes.{key}", expected_page=page)

    receipts = _mapping(card, "receipts")
    _text_list(receipts.get("source_records"), path="receipts.source_records")
    _evidence_records(
        receipts.get("source_record_details"), path="receipts.source_record_details"
    )
    _validate_evidence_identity(
        receipts.get("evidence_identity"), path="receipts.evidence_identity"
    )
    _text_list(
        receipts.get("evidence_identity_refs"), path="receipts.evidence_identity_refs"
    )
    _text_list(
        receipts.get("independent_evidence_families"),
        path="receipts.independent_evidence_families",
    )
    _validate_clock_map(receipts.get("clocks"), path="receipts.clocks")
    if not isinstance(receipts.get("watermarks"), Mapping):
        raise CardPresentationError("receipts.watermarks must be a mapping")
    _validate_bar_status(receipts.get("bar_status"), path="receipts.bar_status")
    if not isinstance(receipts.get("correction_lineage"), Mapping):
        raise CardPresentationError("receipts.correction_lineage must be a mapping")
    _validate_authority(
        _mapping(card, "authority"), path="authority", include_true=True
    )

    card["component_version"] = COMPONENT_VERSION
    card["axis_order"] = AXES
    card["axis_labels"] = AXIS_LABELS
    return card


def render_card(raw: Mapping[str, Any], *, templates_dir: Path | None = None) -> str:
    """Render one validated card with the canonical Jinja macro."""
    card = validate_presentation(raw)
    base = templates_dir or Path(__file__).resolve().parents[1] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(base)),
        autoescape=select_autoescape(("html", "j2")),
        undefined=StrictUndefined,
    )
    template = env.get_template("_theme_opportunity_card.html.j2")
    return str(template.module.theme_opportunity_card(card))
