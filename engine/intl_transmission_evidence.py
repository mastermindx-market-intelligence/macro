"""Typed transmission evidence for International Markets (IM17) — contract only.

Two vocabulary owners, one contract:

* ``config/intl_transmission_channels_v1.json`` — the seven typed channels,
  five pathway labels, four glyph families, candidate sources with their
  rights-matrix rows, evidence/indicator families, receivers, the receiver
  session, global factors and the two read-only frozen models.
* this module — edges, the qualified transmission event, the eligible US
  receiver window derived from the four observation clocks, the retained
  common-global-shock alternative and the deterministic US relevance ordering.

The engine imports neither frozen model (``engine/contagion_links.py``,
``engine/contagion.py``); the tests alone read them, read-only, to prove their
invariance. This module computes no graph score, centrality, percentile or
connectedness, averages no countries and invents no weight: every ordering is
lexicographic over ordinal components that it explains, and every exposure
keeps its own denominator. A null rights row withholds the value; nothing is
ever emitted as zero.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime, time as dtime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.intl_global_observation import (
    CONTRACT_VERSION as OBSERVATION_CONTRACT,
    check_clocks,
)
from engine.intl_global_universe import (
    CAPABILITY_STATES,
    load_rights_matrix,
    load_universe,
)
from engine.theme_graph.rights import EMISSION_OK

CONTRACT_VERSION = "intl-transmission-evidence-v1"
CHANNELS_FILE = "config/intl_transmission_channels_v1.json"

PATHWAYS = (
    "observed_source_stress",
    "documented_exposure",
    "statistical_association",
    "hypothetical_scenario",
    "observed_recipient_corroboration",
)
CHANNELS = (
    "dollar_funding",
    "sovereign_banking",
    "portfolio_fund_ownership",
    "trade_earnings",
    "commodity_terms_of_trade",
    "leverage_liquidity",
    "common_global_shock",
)
GLYPH_FAMILIES = ("flow", "lending", "credit", "commodity")

MODEL_STATUSES = (
    "observed_qualified",
    "documented_source",
    "statistical_estimate_frozen",
    "research_candidate_unpromoted",
    "structural_prior_frozen",
    "scenario_assumption",
)
PATHWAY_MODEL_STATUS = {
    "observed_source_stress": {"observed_qualified"},
    "documented_exposure": {"documented_source"},
    "statistical_association": {"statistical_estimate_frozen",
                                "research_candidate_unpromoted"},
    "hypothetical_scenario": {"structural_prior_frozen", "scenario_assumption"},
    "observed_recipient_corroboration": {"observed_qualified"},
}

DIRECTION_SUPPORT = ("documented", "statistical_candidate", "unsupported")
DIRECTIONS = ("up", "down")

# Aligned by value with engine/intl_global_dislocation.ATTENTION_LABELS (IM15);
# the alignment is pinned by the test — this module never imports IM15.
STRESS_LABELS = ("outside_reference_range", "within_reference_range")
SEVERITY_TIERS = ("none", "within_reference_range", "outside_reference_range",
                  "outside_reference_range_persistent")

RESPONSE_STATUSES = ("pending", "responded_consistent", "responded_inconsistent",
                     "responded_direction_not_assessed", "absent", "ineligible",
                     "unavailable")
US_RESPONSE_STAGES = ("pending", "absent", "mixed", "corroborating",
                      "not_assessed")
ORIGIN_STAGES = ("local_stress", "regional_spread_candidate")
ATTRIBUTIONS = ("common_global_shock_favored", "bilateral_channel_candidate",
                "undetermined")
COMMON_SHOCK_STATUSES = ("favored", "live", "not_indicated")
ALTERNATIVE_IDS = ("common_global_shock", "receiver_idiosyncratic")
CONFIDENCE_LEVELS = ("insufficient", "single_family", "independent_families")

EVENT_ABSTAIN_REASONS = frozenset({
    "origin_not_qualified", "origin_is_receiver", "clock_missing",
    "clock_order_violation", "stress_unqualified", "no_receiver_sessions"})

DISPLAY_STATES = ("shown", "withheld_rights_unresolved", "withheld_no_rights_row",
                  "unavailable")

FORBIDDEN_OUTPUT_KEY_PARTS = ("score", "centrality", "percentile",
                              "connectedness", "country_exposure",
                              "total_exposure", "exposure_pct", "composite")
CAUSAL_TERMS_EN = ("caused", "causes", "causing", "cause of", "drove", "drives",
                   "driven by", "triggered", "triggers", "led to",
                   "spilled over", "contagion from")
CAUSAL_TERMS_ZH = ("导致", "引发", "造成", "传染")

ORDERING_RULE = ("lexicographic:stress_tier>independent_breadth>"
                 "receiver_relevance>observation_eligibility>evidence_quality>"
                 "market_id>event_id")

PERSISTENCE_MIN_SESSIONS = 2
COMMON_SHOCK_MIN_MARKETS = 3
COMMON_SHOCK_MIN_REGIONS = 2
CORROBORATION_MIN_FAMILIES = 2

REGIONS = ("americas", "asia_pacific", "europe", "middle_east_africa")

_HOUSE_MODELS = ("contagion_links", "contagion_dy_var_14etf")

#: Closed per-stage language ceilings; build_event and the summaries draw only
#: from this table, and the causal-language scan keeps every entry clean.
LANGUAGE_CEILINGS = {
    "pending": ("The US recipient window is open and the response is not yet "
                "assessable.",
                "美国接收方窗口已开启，响应尚不可评估。"),
    "absent": ("No eligible US recipient response appears in the assessed "
               "window.",
               "评估窗口内没有符合条件的美国接收方响应。"),
    "mixed": ("US recipient evidence is mixed across receivers or evidence "
              "families.",
              "美国接收方证据在不同接收方或证据族之间表现不一。"),
    "corroborating": ("Recipient corroboration (US evidence) is consistent with "
                      "the proposed channel; it does not establish that the "
                      "origin produced the response.",
                      "接收方佐证（美国证据）与所提渠道一致；它不能证明源头产生了该响应。"),
    "not_assessed": ("No US recipient response was assessed for this event.",
                     "本事件未评估美国接收方响应。"),
}

_ATTRIBUTION_SENTENCES = {
    "common_global_shock_favored": (
        "A common global shock is the favored explanation for the coincidence.",
        "共同全球冲击是这一同步现象的优先解释。"),
    "bilateral_channel_candidate": (
        "A bilateral channel for the proposed link remains a candidate.",
        "所提联系的双边渠道仍为候选。"),
    "undetermined": (
        "The attribution between channel and common shock stays undetermined.",
        "渠道与共同冲击之间的归因仍未确定。"),
}

#: Closed summary templates keyed by (us_response_stage, attribution); the two
#: placeholders are filled with config pathway/channel labels and the retained
#: alternative statuses, never with free prose.
_SUMMARY_TEMPLATES = {}
for _stage in US_RESPONSE_STAGES:
    for _attr in ATTRIBUTIONS:
        _SUMMARY_TEMPLATES[(_stage, _attr)] = (
            LANGUAGE_CEILINGS[_stage][0] + " "
            + _ATTRIBUTION_SENTENCES[_attr][0]
            + " Pathways in evidence: {pathways_en}. Retained alternatives: "
              "common global shock ({cs}); receiver idiosyncratic (live).",
            LANGUAGE_CEILINGS[_stage][1]
            + _ATTRIBUTION_SENTENCES[_attr][1]
            + " 证据路径：{pathways_zh}。保留的替代解释：共同全球冲击（{cs}）；"
              "接收方特质（live）。",
        )
del _stage, _attr

_COMMON_SHOCK_BASIS = {
    "favored": ("A stressed global factor coincides with stressed markets "
                "across at least two regions, so the common global shock "
                "explanation is favored over a bilateral channel.",
                "承压的全球因子与至少两个区域的市场压力同时出现，共同全球冲击解释"
                "优先于双边渠道。"),
    "live": ("The common global shock explanation stays live next to the "
             "proposed channel.",
             "共同全球冲击解释与所提渠道并行保留。"),
    "not_indicated": ("No stressed global factor and insufficient cross-region "
                      "breadth on this session; the common global shock "
                      "explanation is not indicated.",
                      "本交易日无承压全球因子且跨区域广度不足，不指示共同全球冲击。"),
}

_IDIOSYNCRATIC_ALTERNATIVE = {
    "id": "receiver_idiosyncratic",
    "status": "live",
    "basis_en": ("A US-specific response remains a separate possible read of "
                 "the same window."),
    "basis_zh": "美国自身的响应仍是对同一窗口的另一种解读。",
}

_COMPONENT_NAMES = ("stress_tier", "independent_breadth", "receiver_relevance",
                    "observation_eligibility", "evidence_quality")
_COMPONENT_EXPLANATIONS = {
    "stress_tier": ("Index of the event severity tier in the closed tier "
                    "order.", "事件严重程度在封闭档位序列中的序号。"),
    "independent_breadth": ("Count of distinct independent evidence families "
                            "behind the event.",
                            "事件背后不同独立证据族的数量。"),
    "receiver_relevance": ("Highest standing of an edge that names a US "
                           "receiver, from shown documented exposure down to "
                           "none.", "指向美国接收方证据边的最高等级，从已展示的记录敞口到无。"),
    "observation_eligibility": ("Whether a US receiver response was assessed "
                                "inside the eligible window.",
                                "是否有美国接收方响应已在合格窗口内得到评估。"),
    "evidence_quality": ("Count of edges that carry a vintage date, emission "
                         "permission and qualified coverage.",
                         "带有日期、发布许可与合格覆盖的证据边数量。"),
}

_EDGE_KEYS = ("contract_version", "edge_id", "origin_market", "receiver",
              "channel", "glyph_family", "pathway", "pathway_label_en",
              "pathway_label_zh", "model_status", "evidence_family",
              "underlying_id", "source", "vintage", "measure_id", "units",
              "interpretation_en", "interpretation_zh", "direction", "coverage",
              "revision", "value")

_WINDOW_KEYS = ("state", "reason", "knowable_at", "first_qualified_at",
                "measurement_basis", "receiver_session", "start", "end",
                "start_et", "end_et", "same_session_as_knowable", "latency")

_SUMMARY_KEYS = ("contract_version", "event_id", "origin_market",
                 "us_response_stage", "attribution", "alternative_explanations",
                 "edges", "summary_en", "summary_zh")


class TransmissionError(ValueError):
    """Malformed transmission-evidence request; the contract never guesses."""


# ---------------------------------------------------------------------------
# Config access and scans
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_channels(path: str | Path | None = None) -> dict:
    """The frozen transmission-channels document (read-only)."""
    p = Path(path) if path is not None else _repo_root() / CHANNELS_FILE
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _channels_doc(channels) -> dict:
    return load_channels() if channels is None else channels


def _matrix_rows(matrix) -> dict:
    doc = load_rights_matrix() if matrix is None else matrix
    return {row.get("id"): row for row in (doc.get("rows") or [])
            if isinstance(row, dict) and row.get("id")}


def _channel_by_id(doc: dict, channel_id: str) -> dict:
    for channel in doc["channels"]:
        if channel["id"] == channel_id:
            return channel
    raise TransmissionError(f"unknown_channel:{channel_id}")


def _receiver_ids(doc: dict) -> tuple:
    return tuple(r["id"] for r in doc["receivers"])


def _pathway_labels(doc: dict) -> dict:
    return {p["id"]: (p["label_en"], p["label_zh"]) for p in doc["pathways"]}


_SCANNED_KEY_SUFFIXES = ("_en", "_zh")
_SCANNED_KEY_EXACT = frozenset({"interpretation_en", "interpretation_zh",
                                "definition_en", "summary_en", "summary_zh"})


def scan_causal_language(doc) -> list[str]:
    """Dotted paths of scanned text values that carry causal language.

    Walks dicts and lists; a string value is scanned only when its key ends in
    ``_en``/``_zh`` or is one of the named summary/definition keys. Ids and
    model ids are never scanned.
    """
    hits: list[str] = []

    def _scan_text(value: str, path: str) -> None:
        low = value.lower()
        for term in CAUSAL_TERMS_EN:
            if term in low:
                hits.append(path)
                return
        for term in CAUSAL_TERMS_ZH:
            if term in value:
                hits.append(path)
                return

    def walk(node, prefix: str) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if (isinstance(val, str)
                        and (str(key).endswith(_SCANNED_KEY_SUFFIXES)
                             or str(key) in _SCANNED_KEY_EXACT)):
                    _scan_text(val, path)
                else:
                    walk(val, path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{prefix}.{i}" if prefix else str(i))

    walk(doc, "")
    return hits


def forbidden_keys(doc) -> list[str]:
    """Dotted paths of keys (at any depth) naming a forbidden output part."""
    hits: list[str] = []

    def walk(node, prefix: str) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                low = str(key).lower()
                if any(part in low for part in FORBIDDEN_OUTPUT_KEY_PARTS):
                    hits.append(path)
                walk(val, path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{prefix}.{i}" if prefix else str(i))

    walk(doc, "")
    return hits


def validate_channels(doc: dict, matrix: dict | None = None) -> list[str]:
    """Errors in the channels document; an empty list means valid."""
    if not isinstance(doc, dict):
        return ["channels_doc_not_a_dict"]
    errors: list[str] = []
    if doc.get("schema") != "intl-transmission-channels-v1":
        errors.append("schema")
    if doc.get("contract_version") != CONTRACT_VERSION:
        errors.append("contract_version")

    pathways = doc.get("pathways") or []
    if [p.get("id") for p in pathways] != list(PATHWAYS):
        errors.append("pathway_ids")
    for p in pathways:
        for field in ("id", "label_en", "label_zh", "definition_en"):
            if not isinstance(p.get(field), str) or not p[field].strip():
                errors.append(f"pathways.{p.get('id')}.{field}")

    channels = doc.get("channels") or []
    if [c.get("id") for c in channels] != list(CHANNELS):
        errors.append("channel_ids")
    rows = _matrix_rows(matrix)
    kinds = set(doc.get("exposure_kinds") or [])
    families = set(doc.get("evidence_families") or [])
    for c in channels:
        cid = c.get("id")
        glyph = c.get("glyph_family")
        if cid == "common_global_shock":
            if glyph is not None:
                errors.append(f"channels.{cid}.glyph_family_must_be_null")
        elif glyph not in GLYPH_FAMILIES:
            errors.append(f"channels.{cid}.glyph_family")
        for field in ("label_en", "label_zh", "source_side_en",
                      "structural_link_en", "recipient_corroboration_en"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                errors.append(f"channels.{cid}.{field}")
        seen_sources: set[str] = set()
        for cs in c.get("candidate_sources") or []:
            sid = cs.get("source_id")
            if sid in seen_sources:
                errors.append(f"channels.{cid}.duplicate_source:{sid}")
            seen_sources.add(sid)
            ref = cs.get("rights_ref")
            if ref is not None and ref not in rows:
                errors.append(
                    f"channels.{cid}.candidate_sources.{sid}.rights_ref_unknown")
            if cs.get("exposure_kind") not in kinds:
                errors.append(
                    f"channels.{cid}.candidate_sources.{sid}.exposure_kind")
            for field in ("measure_id", "units", "denominator",
                          "interpretation_en", "interpretation_zh"):
                if not isinstance(cs.get(field), str) or not cs[field].strip():
                    errors.append(
                        f"channels.{cid}.candidate_sources.{sid}.{field}")

    for fid, family in (doc.get("indicator_families") or {}).items():
        if family not in families:
            errors.append(f"indicator_families.{fid}")
    for r in doc.get("receivers") or []:
        if r.get("evidence_family") not in families:
            errors.append(f"receivers.{r.get('id')}.evidence_family")
    for f in doc.get("global_factors") or []:
        ref = f.get("rights_ref")
        if ref is not None and ref not in rows:
            errors.append(f"global_factors.{f.get('id')}.rights_ref_unknown")

    sg = doc.get("structural_graph") or {}
    if sg.get("access") != "read_only":
        errors.append("structural_graph.access")
    sm = doc.get("statistical_model") or {}
    if sm.get("access") != "read_only":
        errors.append("statistical_model.access")

    th = doc.get("thresholds") or {}
    for name, expected in (("PERSISTENCE_MIN_SESSIONS", PERSISTENCE_MIN_SESSIONS),
                           ("COMMON_SHOCK_MIN_MARKETS", COMMON_SHOCK_MIN_MARKETS),
                           ("COMMON_SHOCK_MIN_REGIONS", COMMON_SHOCK_MIN_REGIONS),
                           ("CORROBORATION_MIN_FAMILIES",
                            CORROBORATION_MIN_FAMILIES)):
        if th.get(name) != expected:
            errors.append(f"thresholds.{name}")

    errors.extend(scan_causal_language(doc))
    return errors


# ---------------------------------------------------------------------------
# Universe helpers
# ---------------------------------------------------------------------------

def _universe_doc(universe) -> dict:
    return load_universe() if universe is None else universe


def _market_entry(market_id, universe) -> dict:
    doc = _universe_doc(universe)
    jurisdictions = doc.get("jurisdictions") or {}
    aggregates = doc.get("aggregates") or {}
    if market_id in jurisdictions:
        return jurisdictions[market_id]
    if market_id in aggregates:
        return aggregates[market_id]
    raise TransmissionError(f"unknown_market:{market_id}")


def _region_of(market_id, universe) -> str:
    doc = _universe_doc(universe)
    if market_id in (doc.get("aggregates") or {}):
        # The euro-area aggregate carries no region field; it reads as Europe.
        return "europe"
    entry = _market_entry(market_id, doc)
    region = entry.get("region")
    if region not in REGIONS:
        raise TransmissionError(f"unknown_region:{market_id}")
    return region


def _parse_instant(text) -> datetime | None:
    try:
        return datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except (AttributeError, ValueError, TypeError):
        return None


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:  # a naive value is UTC
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _fmt_utc(moment: datetime) -> str:
    return _as_utc(moment).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sessions_list(receiver_sessions) -> list[str]:
    out: set[str] = set()
    for raw in receiver_sessions or ():
        text = str(raw).strip()
        if not text:
            continue
        try:
            date.fromisoformat(text[:10])
        except ValueError as exc:
            raise TransmissionError(f"receiver_session:{text}") from exc
        out.add(text[:10])
    return sorted(out)


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _edge_id(payload: dict) -> str:
    return "tedge:sha256:" + hashlib.sha256(
        _canonical(payload).encode("utf-8")).hexdigest()


def _resolve_rights(source_id: str, channel: dict, matrix) -> dict:
    """Rights resolution for one source inside one channel."""
    candidate = None
    for cs in channel.get("candidate_sources") or []:
        if cs["source_id"] == source_id:
            candidate = cs
            break
    if candidate is not None:
        ref = candidate.get("rights_ref")
        if ref is None:
            return {"source_id": source_id, "rights_ref": None,
                    "rights_class": None, "authority": "no_rights_row",
                    "emission_permitted": False}
        row = _matrix_rows(matrix).get(ref)
        if row is None:
            raise TransmissionError(f"rights_ref_unknown:{ref}")
        klass = row.get("rights_class")
        permitted = klass in EMISSION_OK
        return {"source_id": source_id, "rights_ref": ref,
                "rights_class": klass, "authority": "rights_matrix",
                "emission_permitted": permitted}
    if source_id in _HOUSE_MODELS:
        return {"source_id": source_id, "rights_ref": None, "rights_class": None,
                "authority": "house_model", "emission_permitted": True}
    raise TransmissionError(f"unknown_source_for_channel:{source_id}")


def build_edge(*, origin_market, receiver, channel, pathway, model_status,
               source_id, measure_id, units, interpretation_en,
               interpretation_zh, evidence_family, as_of=None,
               published_at=None, direction=None, direction_support="unsupported",
               coverage_state="unavailable", coverage_basis="", amount=None,
               denominator=None, exposure_kind=None, revision=0,
               supersedes=None, underlying_id=None, channels=None,
               matrix=None, universe=None) -> dict:
    """One typed origin-to-US edge, or a refusal with a closed reason."""
    doc = _channels_doc(channels)
    if origin_market == "US":
        raise TransmissionError("origin_is_receiver")
    _market_entry(origin_market, universe)
    if receiver not in _receiver_ids(doc):
        raise TransmissionError(f"unknown_receiver:{receiver}")
    if channel not in CHANNELS:
        raise TransmissionError(f"unknown_channel:{channel}")
    if channel == "common_global_shock":
        raise TransmissionError("common_global_shock_is_not_bilateral")
    if not isinstance(pathway, str) or not pathway:
        raise TransmissionError("pathway_must_be_exactly_one_string")
    if pathway not in PATHWAYS:
        raise TransmissionError(f"unknown_pathway:{pathway}")
    if (model_status not in MODEL_STATUSES
            or model_status not in PATHWAY_MODEL_STATUS[pathway]):
        raise TransmissionError(
            f"pathway_model_status:{pathway}/{model_status}")
    if evidence_family not in doc["evidence_families"]:
        raise TransmissionError(f"unknown_evidence_family:{evidence_family}")
    if direction is not None and direction not in DIRECTIONS:
        raise TransmissionError(f"direction:{direction}")
    if direction_support not in DIRECTION_SUPPORT:
        raise TransmissionError(f"direction_support:{direction_support}")
    if direction is not None and direction_support == "unsupported":
        raise TransmissionError("direction_requires_support")
    if coverage_state not in CAPABILITY_STATES:
        raise TransmissionError(f"coverage_state:{coverage_state}")

    channel_doc = _channel_by_id(doc, channel)
    candidate_ids = {cs["source_id"] for cs in
                     channel_doc.get("candidate_sources") or []}
    if (source_id not in candidate_ids) and (source_id not in _HOUSE_MODELS):
        raise TransmissionError(f"unknown_source_for_channel:{source_id}")

    if pathway == "documented_exposure":
        if as_of is None:
            raise TransmissionError("documented_exposure_requires_as_of")
        if exposure_kind is None:
            raise TransmissionError("documented_exposure_requires_exposure_kind")
        if denominator is None:
            raise TransmissionError("documented_exposure_requires_denominator")
        if source_id not in candidate_ids:
            raise TransmissionError("documented_exposure_source_not_candidate")
    if (pathway == "hypothetical_scenario"
            and model_status == "structural_prior_frozen"):
        graph_markets = {m.lower() for m in
                         doc["structural_graph"]["markets"]}
        if origin_market.lower() not in graph_markets:
            raise TransmissionError("origin_outside_structural_graph")
    if (pathway == "statistical_association"
            and model_status == "statistical_estimate_frozen"
            and source_id != doc["statistical_model"]["model_id"]):
        raise TransmissionError("statistical_estimate_frozen_requires_dy_model")

    source = _resolve_rights(source_id, channel_doc, matrix)
    if amount is None:
        display = "unavailable"
    elif not source["emission_permitted"]:
        display = ("withheld_rights_unresolved"
                   if source["authority"] == "rights_matrix"
                   else "withheld_no_rights_row")
    else:
        display = "shown"
    emitted_amount = amount if display == "shown" else None

    label_en, label_zh = _pathway_labels(doc)[pathway]
    return {
        "contract_version": CONTRACT_VERSION,
        "edge_id": _edge_id({"origin_market": origin_market, "receiver": receiver,
                             "channel": channel, "pathway": pathway,
                             "source_id": source_id, "measure_id": measure_id,
                             "as_of": as_of, "revision": revision}),
        "origin_market": origin_market,
        "receiver": receiver,
        "channel": channel,
        "glyph_family": channel_doc.get("glyph_family"),
        "pathway": pathway,
        "pathway_label_en": label_en,
        "pathway_label_zh": label_zh,
        "model_status": model_status,
        "evidence_family": evidence_family,
        "underlying_id": underlying_id,
        "source": source,
        "vintage": {"as_of": as_of, "published_at": published_at},
        "measure_id": measure_id,
        "units": units,
        "interpretation_en": interpretation_en,
        "interpretation_zh": interpretation_zh,
        "direction": {"expected_receiver_direction": direction,
                      "support": direction_support},
        "coverage": {"state": coverage_state, "basis": coverage_basis},
        "revision": {"revision": revision, "supersedes": supersedes},
        "value": {"amount": emitted_amount, "denominator": denominator,
                  "exposure_kind": exposure_kind, "display": display},
    }


def validate_edge(edge) -> None:
    """Re-check every build rule plus internal consistency on an emitted edge."""
    doc = load_channels()
    if not isinstance(edge, dict) or tuple(edge) != _EDGE_KEYS:
        raise TransmissionError("edge_fields")
    if edge["contract_version"] != CONTRACT_VERSION:
        raise TransmissionError("edge_contract_version")
    origin = edge["origin_market"]
    if origin == "US":
        raise TransmissionError("origin_is_receiver")
    _market_entry(origin, None)
    if edge["receiver"] not in _receiver_ids(doc):
        raise TransmissionError(f"unknown_receiver:{edge['receiver']}")
    channel = edge["channel"]
    if channel not in CHANNELS or channel == "common_global_shock":
        raise TransmissionError(f"unknown_channel:{channel}")
    channel_doc = _channel_by_id(doc, channel)
    if edge["glyph_family"] != channel_doc.get("glyph_family"):
        raise TransmissionError("glyph_family_mismatch")
    pathway = edge["pathway"]
    if not isinstance(pathway, str) or pathway not in PATHWAYS:
        raise TransmissionError(f"unknown_pathway:{pathway}")
    if edge["model_status"] not in PATHWAY_MODEL_STATUS[pathway]:
        raise TransmissionError(f"pathway_model_status:{pathway}")
    expected_labels = _pathway_labels(doc)[pathway]
    if (edge["pathway_label_en"], edge["pathway_label_zh"]) != expected_labels:
        raise TransmissionError("pathway_label_mismatch")
    if edge["evidence_family"] not in doc["evidence_families"]:
        raise TransmissionError(f"unknown_evidence_family:{edge['evidence_family']}")
    direction = edge["direction"]
    if tuple(direction) != ("expected_receiver_direction", "support"):
        raise TransmissionError("direction_fields")
    if (direction["expected_receiver_direction"] is not None
            and direction["expected_receiver_direction"] not in DIRECTIONS):
        raise TransmissionError("direction")
    if direction["support"] not in DIRECTION_SUPPORT:
        raise TransmissionError("direction_support")
    if (direction["expected_receiver_direction"] is not None
            and direction["support"] == "unsupported"):
        raise TransmissionError("direction_requires_support")
    coverage = edge["coverage"]
    if tuple(coverage) != ("state", "basis"):
        raise TransmissionError("coverage_fields")
    if coverage["state"] not in CAPABILITY_STATES:
        raise TransmissionError("coverage_state")

    source_id = edge["source"]["source_id"]
    candidate_ids = {cs["source_id"] for cs in
                     channel_doc.get("candidate_sources") or []}
    if (source_id not in candidate_ids) and (source_id not in _HOUSE_MODELS):
        raise TransmissionError(f"unknown_source_for_channel:{source_id}")
    if pathway == "documented_exposure":
        if edge["vintage"]["as_of"] is None:
            raise TransmissionError("documented_exposure_requires_as_of")
        if edge["value"]["exposure_kind"] is None:
            raise TransmissionError("documented_exposure_requires_exposure_kind")
        if edge["value"]["denominator"] is None:
            raise TransmissionError("documented_exposure_requires_denominator")
        if source_id not in candidate_ids:
            raise TransmissionError("documented_exposure_source_not_candidate")
    if (pathway == "hypothetical_scenario"
            and edge["model_status"] == "structural_prior_frozen"):
        graph_markets = {m.lower() for m in doc["structural_graph"]["markets"]}
        if origin.lower() not in graph_markets:
            raise TransmissionError("origin_outside_structural_graph")
    if (pathway == "statistical_association"
            and edge["model_status"] == "statistical_estimate_frozen"
            and source_id != doc["statistical_model"]["model_id"]):
        raise TransmissionError("statistical_estimate_frozen_requires_dy_model")

    src, val = edge["source"], edge["value"]
    if tuple(src) != ("source_id", "rights_ref", "rights_class", "authority",
                      "emission_permitted"):
        raise TransmissionError("source_fields")
    if tuple(val) != ("amount", "denominator", "exposure_kind", "display"):
        raise TransmissionError("value_fields")
    if src["authority"] not in ("rights_matrix", "no_rights_row", "house_model"):
        raise TransmissionError("authority")
    if source_id in _HOUSE_MODELS:
        if src["authority"] != "house_model" or not src["emission_permitted"]:
            raise TransmissionError("house_model_rights")
    elif src["rights_ref"] is None:
        if (src["authority"] != "no_rights_row"
                or src["emission_permitted"] is not False):
            raise TransmissionError("no_rights_row_consistency")
    else:
        if src["authority"] != "rights_matrix":
            raise TransmissionError("rights_matrix_consistency")
        if src["emission_permitted"] is not (src["rights_class"] in EMISSION_OK):
            raise TransmissionError("emission_consistency")
    display = val["display"]
    if display not in DISPLAY_STATES:
        raise TransmissionError(f"display:{display}")
    if display == "shown":
        if not src["emission_permitted"] or val["amount"] is None:
            raise TransmissionError("shown_requires_emission_and_amount")
    else:
        if val["amount"] is not None:
            raise TransmissionError("withheld_or_unavailable_amount_must_be_null")
    if edge["edge_id"] != _edge_id({
            "origin_market": origin, "receiver": edge["receiver"],
            "channel": channel, "pathway": pathway, "source_id": source_id,
            "measure_id": edge["measure_id"],
            "as_of": edge["vintage"]["as_of"],
            "revision": edge["revision"]["revision"]}):
        raise TransmissionError("edge_id_mismatch")


# ---------------------------------------------------------------------------
# Evidence families and the receiver window
# ---------------------------------------------------------------------------

def evidence_families(indicators, channels=None) -> list[str]:
    """Sorted distinct families of outside-range indicators.

    Two indicators sharing an ``underlying_id`` count once; only
    ``outside_reference_range`` labels count.
    """
    doc = _channels_doc(channels)
    table = doc.get("indicator_families") or {}
    families: set[str] = set()
    seen: set = set()
    for position, item in enumerate(indicators or []):
        if not isinstance(item, dict):
            raise TransmissionError("indicator_shape")
        indicator_id = item.get("indicator_id")
        if indicator_id not in table:
            raise TransmissionError(f"unknown_indicator:{indicator_id}")
        if item.get("attention_label") != "outside_reference_range":
            continue
        underlying = item.get("underlying_id")
        key = ("uid", underlying) if underlying is not None else ("pos", position)
        if key in seen:
            continue
        seen.add(key)
        families.add(table[indicator_id])
    return sorted(families)


def receiver_window(observation: dict, receiver_sessions, channels=None) -> dict:
    """The earliest measurable US receiver window at or after knowable-at."""
    doc = _channels_doc(channels)
    if (not isinstance(observation, dict)
            or observation.get("contract_version") != OBSERVATION_CONTRACT):
        raise TransmissionError("observation_contract_version")

    def abstain(reason: str) -> dict:
        out = {key: None for key in _WINDOW_KEYS}
        out["state"] = "abstain"
        out["reason"] = reason
        return out

    clocks = observation.get("clocks")
    clock_reason = check_clocks(clocks)
    if clock_reason is not None:
        return abstain(clock_reason)
    sessions = _sessions_list(receiver_sessions)
    if not sessions:
        return abstain("no_receiver_sessions")

    publication = clocks["source_publication"]
    published_at = _parse_instant(publication.get("at"))
    if published_at is None:
        return abstain("clock_missing")
    session_cfg = doc["receiver_session"]
    zone = ZoneInfo(session_cfg["tz"])
    if publication.get("precision") == "session_date":
        knowable = datetime.combine(
            published_at.date(), dtime(23, 59, 59), tzinfo=zone)
    else:
        knowable = _as_utc(published_at)
    knowable_utc = _as_utc(knowable)

    open_time = dtime.fromisoformat(session_cfg["open"])
    close_time = dtime.fromisoformat(session_cfg["close"])
    intervals = []
    for index, session in enumerate(sessions):
        day = date.fromisoformat(session)
        session_close = datetime.combine(day, close_time, tzinfo=zone)
        intervals.append((
            "open_to_close",
            datetime.combine(day, open_time, tzinfo=zone),
            session_close, session))
        if index:
            previous = date.fromisoformat(sessions[index - 1])
            intervals.append((
                "close_to_close",
                datetime.combine(previous, close_time, tzinfo=zone),
                session_close, session))
    eligible = [item for item in intervals
                if _as_utc(item[1]) >= knowable_utc]
    if not eligible:
        return abstain("no_receiver_sessions")
    basis, start_et, end_et, session = min(
        eligible,
        key=lambda item: (_as_utc(item[1]),
                          0 if item[0] == "open_to_close" else 1))

    ingestion = _parse_instant(clocks["ingestion"]["at"])
    computation = _parse_instant(clocks["computation"]["at"])
    latency = {}
    if ingestion is not None:
        latency["publication_to_ingestion_s"] = int(
            (_as_utc(ingestion) - _as_utc(published_at)).total_seconds())
    else:
        latency["publication_to_ingestion_s"] = None
    if ingestion is not None and computation is not None:
        latency["ingestion_to_computation_s"] = int(
            (_as_utc(computation) - _as_utc(ingestion)).total_seconds())
    else:
        latency["ingestion_to_computation_s"] = None

    return {
        "state": "qualified",
        "reason": None,
        "knowable_at": _fmt_utc(knowable_utc),
        "first_qualified_at": clocks["computation"]["at"],
        "measurement_basis": basis,
        "receiver_session": session,
        "start": _fmt_utc(_as_utc(start_et)),
        "end": _fmt_utc(_as_utc(end_et)),
        "start_et": start_et.isoformat(),
        "end_et": end_et.isoformat(),
        "same_session_as_knowable": (
            date.fromisoformat(session)
            == knowable_utc.astimezone(zone).date()),
        "latency": latency,
    }


def classify_response(window: dict, response: dict | None, *,
                      expected_directions, as_of: str) -> dict:
    """Closed-vocabulary status for one receiver response in one window."""
    receiver_id = evidence_family = receipt_ref = None
    if response is not None:
        if not isinstance(response, dict):
            raise TransmissionError("response_shape")
        receiver_id = response.get("receiver_id")
        evidence_family = response.get("evidence_family")
        receipt_ref = response.get("receipt_ref")

    def outcome(status: str) -> dict:
        return {"receiver_id": receiver_id, "status": status,
                "evidence_family": evidence_family, "receipt_ref": receipt_ref}

    if not isinstance(window, dict) or window.get("state") != "qualified":
        return outcome("unavailable")
    if response is None:
        return outcome("unavailable")
    as_of_moment = _parse_instant(as_of)
    end_moment = _parse_instant(window.get("end"))
    if as_of_moment is None or end_moment is None:
        raise TransmissionError("classify_instants")
    if _as_utc(as_of_moment) < _as_utc(end_moment):
        return outcome("pending")
    if not response.get("qualified"):
        return outcome("unavailable")
    knowable = _parse_instant(window.get("knowable_at"))
    response_start = _parse_instant(response.get("window_start"))
    response_end = _parse_instant(response.get("window_end"))
    if knowable is None or response_start is None or response_end is None:
        raise TransmissionError("response_window")
    if (_as_utc(response_start) < _as_utc(knowable)
            or _as_utc(response_end) > _as_utc(end_moment)):
        return outcome("ineligible")
    label = response.get("attention_label")
    if label not in STRESS_LABELS:
        raise TransmissionError(f"attention_label:{label}")
    if label == "within_reference_range":
        return outcome("absent")
    directions = {d for d in (expected_directions or ()) if d in DIRECTIONS}
    if len(directions) == 1:
        expected = next(iter(directions))
        return outcome("responded_consistent"
                       if response.get("direction") == expected
                       else "responded_inconsistent")
    return outcome("responded_direction_not_assessed")


# ---------------------------------------------------------------------------
# Common global shock
# ---------------------------------------------------------------------------

def _common_level(factor_hit: bool, n_markets: int, n_regions: int,
                  factors_in, doc) -> str:
    breadth = (n_markets >= COMMON_SHOCK_MIN_MARKETS
               and n_regions >= COMMON_SHOCK_MIN_REGIONS)
    if factor_hit and breadth:
        return "favored"
    if factor_hit or breadth or not factors_in:
        return "live"
    return "not_indicated"


def common_shock_status(*, origin_market, origin_session, global_factors,
                        regional_stress, universe=None, channels=None) -> dict:
    """Status of the retained common-global-shock alternative explanation."""
    doc = _channels_doc(channels)
    uni = _universe_doc(universe)
    configured = {f["id"] for f in doc["global_factors"]}
    factors_in = list(global_factors or [])
    hits: set[str] = set()
    for factor in factors_in:
        if not isinstance(factor, dict):
            raise TransmissionError("global_factor_shape")
        factor_id = factor.get("factor_id")
        if factor_id not in configured:
            raise TransmissionError(f"unknown_global_factor:{factor_id}")
        if (factor.get("session") == origin_session
                and factor.get("attention_label") == "outside_reference_range"):
            hits.add(factor_id)
    factor_hit = bool(hits)

    stressed = {origin_market}
    for market in (regional_stress or []):
        if not isinstance(market, dict):
            raise TransmissionError("regional_stress_shape")
        market_id = market.get("market_id")
        _region_of(market_id, uni)  # unknown markets are refused, not guessed
        if (market.get("session") == origin_session
                and market.get("attention_label") == "outside_reference_range"):
            stressed.add(market_id)
    regions = {_region_of(market_id, uni) for market_id in stressed}

    status = _common_level(factor_hit, len(stressed), len(regions),
                           factors_in, doc)
    basis_en, basis_zh = _COMMON_SHOCK_BASIS[status]
    return {
        "id": "common_global_shock",
        "status": status,
        "stressed_markets": sorted(stressed),
        "region_count": len(regions),
        "factor_hits": sorted(hits),
        "basis_en": basis_en,
        "basis_zh": basis_zh,
    }


# ---------------------------------------------------------------------------
# The qualified transmission event
# ---------------------------------------------------------------------------

def _us_response_stage(statuses, attribution, level) -> str:
    assessed = [s for s in statuses if s not in ("unavailable", "ineligible")]
    if not assessed:
        return "not_assessed"
    if all(s == "pending" for s in assessed):
        return "pending"
    if attribution == "common_global_shock_favored":
        if any(s.startswith("responded_") for s in assessed):
            return "mixed"
        if all(s == "absent" for s in assessed):
            return "absent"
    if (any(s == "responded_consistent" for s in assessed)
            and level == "independent_families"
            and attribution != "common_global_shock_favored"):
        return "corroborating"
    if all(s == "absent" for s in assessed):
        return "absent"
    return "mixed"


def build_event(*, origin_observation, stress, edges, responses,
                global_factors, regional_stress, receiver_sessions, as_of,
                revision=0, supersedes=None, channels=None,
                universe=None) -> dict:
    """One qualified transmission event, or an abstention with closed reasons."""
    doc = _channels_doc(channels)
    uni = _universe_doc(universe)
    if (not isinstance(origin_observation, dict)
            or origin_observation.get("contract_version") != OBSERVATION_CONTRACT):
        raise TransmissionError("observation_contract_version")
    identity = origin_observation.get("identity") or {}
    origin = identity.get("universe_id")
    if not isinstance(origin, str) or not origin:
        raise TransmissionError("origin_identity")
    origin_session = str(identity.get("window_end") or "")[:10]

    if not isinstance(stress, dict):
        raise TransmissionError("stress_shape")
    label = stress.get("attention_label")
    if label is not None and label not in STRESS_LABELS:
        raise TransmissionError(f"stress_label:{label}")
    persistence = stress.get("persistence_sessions", 0)
    if (isinstance(persistence, bool) or not isinstance(persistence, int)
            or persistence < 0):
        raise TransmissionError("stress_persistence")
    indicators = stress.get("indicators")
    if indicators is None:
        indicators = []
    if not isinstance(indicators, list):
        raise TransmissionError("stress_indicators")
    stress_families = evidence_families(indicators, channels=doc)

    reasons: set[str] = set()
    if origin_observation.get("state") != "qualified":
        reasons.add("origin_not_qualified")
    if origin == "US":
        reasons.add("origin_is_receiver")
    window = receiver_window(origin_observation, receiver_sessions, channels=doc)
    if window["state"] != "qualified":
        reasons.add(window["reason"])
    if label is None:
        reasons.add("stress_unqualified")

    edge_list = list(edges or [])
    if reasons:
        common = common_shock_status(
            origin_market=origin, origin_session=origin_session,
            global_factors=global_factors, regional_stress=regional_stress,
            universe=uni, channels=doc)
        return _event_payload(
            observation=origin_observation, origin=origin,
            origin_session=origin_session, stress=stress, state="abstain",
            reasons=sorted(reasons), edges_out=[], first_qualified_at=None,
            affected_markets=[], origin_stage="local_stress", receivers=[],
            stage="not_assessed", attribution="undetermined",
            alternatives=[common, copy.deepcopy(_IDIOSYNCRATIC_ALTERNATIVE)],
            severity_tier="none", families=[], channels_with_evidence=0,
            by_pathway={p: 0 for p in PATHWAYS}, as_of=as_of, revision=revision,
            supersedes=supersedes, edge_ids=[])

    for edge in edge_list:
        if not isinstance(edge, dict) or edge.get("origin_market") != origin:
            raise TransmissionError("edge_origin_mismatch")
        validate_edge(edge)
    ordered = sorted(
        edge_list,
        key=lambda e: (CHANNELS.index(e["channel"]),
                       PATHWAYS.index(e["pathway"]), e["edge_id"]))
    edge_ids = sorted(e["edge_id"] for e in ordered)

    if label == "within_reference_range":
        tier = "within_reference_range"
    elif persistence >= PERSISTENCE_MIN_SESSIONS:
        tier = "outside_reference_range_persistent"
    else:
        tier = "outside_reference_range"

    origin_region = _region_of(origin, uni)
    regional_outside = {
        m.get("market_id") for m in (regional_stress or [])
        if m.get("session") == origin_session
        and m.get("attention_label") == "outside_reference_range"
        and m.get("market_id")}
    same_region = any(
        market_id != origin and _region_of(market_id, uni) == origin_region
        for market_id in regional_outside)
    origin_stage = ("regional_spread_candidate" if same_region
                    else "local_stress")

    response_list = list(responses or [])
    receiver_rows = []
    statuses = []
    response_families: set[str] = set()
    for receiver_id in _receiver_ids(doc):
        supplied = next((r for r in response_list
                         if isinstance(r, dict)
                         and r.get("receiver_id") == receiver_id), None)
        expected = {
            e["direction"]["expected_receiver_direction"] for e in ordered
            if e["receiver"] == receiver_id
            and e["direction"]["support"] != "unsupported"
            and e["direction"]["expected_receiver_direction"] is not None}
        if supplied is not None:
            classified = classify_response(
                window, supplied, expected_directions=expected, as_of=as_of)
        else:
            classified = {"receiver_id": receiver_id, "status": "unavailable",
                          "evidence_family": None, "receipt_ref": None}
        receiver_rows.append({"receiver_id": receiver_id, "window": window,
                              "response": classified})
        statuses.append(classified["status"])
        if classified["status"].startswith("responded_"):
            response_families.add(classified["evidence_family"])

    families = sorted(set(stress_families)
                      | {f for f in response_families if f})
    if not families:
        level = "insufficient"
    elif len(families) < CORROBORATION_MIN_FAMILIES:
        level = "single_family"
    else:
        level = "independent_families"

    common = common_shock_status(
        origin_market=origin, origin_session=origin_session,
        global_factors=global_factors, regional_stress=regional_stress,
        universe=uni, channels=doc)
    if common["status"] == "favored":
        attribution = "common_global_shock_favored"
    elif any(e["pathway"] in ("documented_exposure", "statistical_association")
             for e in ordered):
        attribution = "bilateral_channel_candidate"
    else:
        attribution = "undetermined"
    stage = _us_response_stage(statuses, attribution, level)

    drawable = [c for c in CHANNELS if c != "common_global_shock"]
    by_pathway = {p: 0 for p in PATHWAYS}
    for edge in ordered:
        by_pathway[edge["pathway"]] += 1
    return _event_payload(
        observation=origin_observation, origin=origin,
        origin_session=origin_session, stress=stress, state="qualified",
        reasons=[], edges_out=ordered,
        first_qualified_at=window["first_qualified_at"],
        affected_markets=sorted({origin} | regional_outside),
        origin_stage=origin_stage, receivers=receiver_rows, stage=stage,
        attribution=attribution,
        alternatives=[common, copy.deepcopy(_IDIOSYNCRATIC_ALTERNATIVE)],
        severity_tier=tier, families=families,
        channels_with_evidence=len({e["channel"] for e in ordered}
                                   & set(drawable)),
        by_pathway=by_pathway, as_of=as_of, revision=revision,
        supersedes=supersedes, edge_ids=edge_ids)


def _event_payload(*, observation, origin, origin_session, stress, state,
                   reasons, edges_out, first_qualified_at, affected_markets,
                   origin_stage, receivers, stage, attribution, alternatives,
                   severity_tier, families, channels_with_evidence,
                   by_pathway, as_of, revision, supersedes, edge_ids) -> dict:
    ceiling_en, ceiling_zh = LANGUAGE_CEILINGS[stage]
    return {
        "contract_version": CONTRACT_VERSION,
        "event_id": "tev:sha256:" + hashlib.sha256(_canonical({
            "observation_id": observation.get("observation_id"),
            "origin": origin,
            "edges": sorted(edge_ids),
            "revision": revision}).encode("utf-8")).hexdigest(),
        "state": state,
        "abstain_reasons": reasons,
        "origin": {
            "market_id": origin,
            "observation_id": observation.get("observation_id"),
            "observation_contract": observation.get("contract_version"),
            "session": origin_session,
            "stress": {
                "attention_label": stress.get("attention_label"),
                "persistence_sessions": stress.get("persistence_sessions", 0),
                "receipt_ref": stress.get("receipt_ref")}},
        "first_qualified_at": first_qualified_at,
        "affected_markets": affected_markets,
        "origin_stage": origin_stage,
        "channel_evidence": edges_out,
        "receivers": receivers,
        "us_response_stage": stage,
        "attribution": attribution,
        "alternative_explanations": alternatives,
        "severity": {"tier": severity_tier},
        "confidence": {"level": ("insufficient" if not families else
                                 "single_family"
                                 if len(families) < CORROBORATION_MIN_FAMILIES
                                 else "independent_families"),
                       "independent_family_count": len(families),
                       "families": families},
        "coverage": {"measurement": "channel_count", "channels_total": 6,
                     "channels_with_evidence": channels_with_evidence,
                     "by_pathway": by_pathway},
        "revision": {"revision": revision, "supersedes": supersedes},
        "as_of": as_of,
        "language_ceiling_en": ceiling_en,
        "language_ceiling_zh": ceiling_zh,
    }


# ---------------------------------------------------------------------------
# Per-market summary, rank strip, exposure by kind
# ---------------------------------------------------------------------------

def market_summary(market_id, *, edges, observations, universe=None,
                   channels=None) -> dict:
    """Per-market structural/statistical standing with no invented numbers."""
    doc = _channels_doc(channels)
    uni = _universe_doc(universe)
    entry = _market_entry(market_id, uni)
    graph = doc["structural_graph"]
    member = market_id.lower() in {m.lower() for m in graph["markets"]}
    statistical = doc["statistical_model"]
    instrument = next((ticker for ticker, market in
                       (statistical.get("etf_market") or {}).items()
                       if market == market_id), None)

    edge_list = [e for e in (edges or [])
                 if isinstance(e, dict) and e.get("origin_market") == market_id]

    def ordered(items):
        return sorted(items, key=lambda e: (CHANNELS.index(e["channel"]),
                                            PATHWAYS.index(e["pathway"]),
                                            e["edge_id"]))

    observation_ids = sorted(
        o.get("observation_id") for o in (observations or [])
        if isinstance(o, dict)
        and o.get("contract_version") == OBSERVATION_CONTRACT
        and o.get("state") == "qualified"
        and (o.get("identity") or {}).get("universe_id") == market_id)
    capability = ((entry.get("capabilities") or {}).get("equity_index_fx") or {})
    payload = {
        "market_id": market_id,
        "name": entry.get("name"),
        "region": _region_of(market_id, uni),
        "structural_graph": {
            "model_id": graph["model_id"],
            "structural_version": graph["structural_version"],
            "member": member,
            "state": "member" if member else "outside_structural_graph"},
        "statistical_population": {
            "model_id": statistical["model_id"],
            "member": instrument is not None,
            "instrument": instrument},
        "structural_research": ordered(
            [e for e in edge_list
             if e.get("pathway") in ("documented_exposure",
                                     "hypothetical_scenario")]),
        "statistical_evidence": ordered(
            [e for e in edge_list
             if e.get("pathway") == "statistical_association"]),
        "qualified_observations": {
            "capability_state": capability.get("state"),
            "reason": capability.get("reason"),
            "observation_ids": observation_ids},
        "display_order": (
            ["qualified_observations", "structural_research",
             "statistical_evidence", "structural_graph"] if member
            else ["structural_research", "qualified_observations",
                  "statistical_evidence"]),
    }
    return payload


def channel_rank_strip(origin_market, measures, *, channels=None,
                       matrix=None) -> list[dict]:
    """One row per drawable channel; never mixing denominators."""
    doc = _channels_doc(channels)
    if origin_market == "US":
        raise TransmissionError("origin_is_receiver")
    _market_entry(origin_market, None)
    measure_list = [m for m in (measures or []) if isinstance(m, dict)]
    rows = _matrix_rows(matrix)
    strip = []
    for channel in doc["channels"]:
        if channel["id"] == "common_global_shock":
            continue
        row = {"channel": channel["id"], "glyph_family": channel["glyph_family"],
               "state": None, "reason": None, "measure_id": None, "units": None,
               "denominator": None, "value": None, "rank": None,
               "rank_population": None, "source_id": None, "as_of": None}
        candidates = channel.get("candidate_sources") or []
        preferred = [cs["source_id"] for cs in candidates]
        mine = [m for m in measure_list
                if m.get("market_id") == origin_market
                and m.get("channel") == channel["id"]
                and m.get("source_id") in preferred]
        if not mine:
            row["state"] = "unavailable"
            row["reason"] = "no_admitted_source"
            strip.append(row)
            continue
        chosen = min(mine, key=lambda m: preferred.index(m["source_id"]))
        candidate = next(cs for cs in candidates
                         if cs["source_id"] == chosen["source_id"])
        ref = candidate.get("rights_ref")
        if ref is None:
            permitted = False
            row["state"] = "withheld"
            row["reason"] = "no_rights_row"
        else:
            klass = (rows.get(ref) or {}).get("rights_class")
            permitted = klass in EMISSION_OK
            if not permitted:
                row["state"] = "withheld"
                row["reason"] = "rights_unresolved"
        row["measure_id"] = chosen.get("measure_id")
        row["units"] = chosen.get("units")
        row["denominator"] = chosen.get("denominator")
        row["source_id"] = chosen.get("source_id")
        row["as_of"] = chosen.get("as_of")
        if not permitted:
            strip.append(row)
            continue
        if chosen.get("value") is None:
            row["state"] = "unavailable"
            row["reason"] = "no_qualified_value"
            strip.append(row)
            continue
        row["value"] = chosen.get("value")
        # Population: same channel+measure+units+denominator, permitted, valued.
        population = []
        for m in measure_list:
            if (m.get("channel") != channel["id"]
                    or m.get("measure_id") != chosen.get("measure_id")
                    or m.get("units") != chosen.get("units")
                    or m.get("denominator") != chosen.get("denominator")
                    or m.get("value") is None
                    or m.get("source_id") not in preferred):
                continue
            cs = next(c for c in candidates
                      if c["source_id"] == m["source_id"])
            ref_m = cs.get("rights_ref")
            klass_m = (rows.get(ref_m) or {}).get("rights_class") \
                if ref_m is not None else None
            if klass_m in EMISSION_OK:
                population.append(m["value"])
        row["rank"] = 1 + sum(1 for v in population if v > chosen["value"])
        row["rank_population"] = len(population)
        row["state"] = "shown"
        strip.append(row)
    return strip


def exposure_by_kind(edges) -> dict:
    """Documented exposures grouped by kind; no totals, no cross-kind math."""
    kinds = load_channels()["exposure_kinds"]
    out = {kind: [] for kind in kinds}
    for edge in edges or []:
        if not isinstance(edge, dict) or edge.get("pathway") != "documented_exposure":
            continue
        value = edge.get("value") or {}
        kind = value.get("exposure_kind")
        if kind not in out:
            raise TransmissionError(f"unknown_exposure_kind:{kind}")
        out[kind].append({
            "edge_id": edge.get("edge_id"),
            "units": edge.get("units"),
            "denominator": value.get("denominator"),
            "amount": value.get("amount"),
            "display": value.get("display")})
    return out


# ---------------------------------------------------------------------------
# US relevance ordering and summaries
# ---------------------------------------------------------------------------

def us_relevance_order(events) -> list[dict]:
    """Deterministic lexicographic ordering with explained components."""
    scored = []
    for event in events or []:
        if not isinstance(event, dict):
            raise TransmissionError("event_shape")
        abstained = event.get("state") == "abstain"
        tier = SEVERITY_TIERS.index(
            (event.get("severity") or {}).get("tier", "none"))
        breadth = 0 if abstained else len(
            (event.get("confidence") or {}).get("families") or [])
        edges = event.get("channel_evidence") or []
        documented = [e for e in edges
                      if e.get("pathway") == "documented_exposure"]
        if any((e.get("value") or {}).get("display") == "shown"
               for e in documented):
            relevance = 3
        elif documented:
            relevance = 2
        elif any(e.get("pathway") in ("statistical_association",
                                      "hypothetical_scenario") for e in edges):
            relevance = 1
        else:
            relevance = 0
        statuses = [((r.get("response") or {}).get("status"))
                    for r in event.get("receivers") or []]
        if any(s not in ("pending", "unavailable", "ineligible")
               for s in statuses):
            eligibility = 2
        elif any(s == "pending" for s in statuses):
            eligibility = 1
        else:
            eligibility = 0
        quality = sum(
            1 for e in edges
            if (e.get("vintage") or {}).get("as_of") is not None
            and (e.get("source") or {}).get("emission_permitted")
            and (e.get("coverage") or {}).get("state") == "qualified")
        scored.append({
            "market_id": (event.get("origin") or {}).get("market_id"),
            "event_id": event.get("event_id"),
            "components": {"stress_tier": tier,
                           "independent_breadth": breadth,
                           "receiver_relevance": relevance,
                           "observation_eligibility": eligibility,
                           "evidence_quality": quality}})
    scored.sort(key=lambda r: (-r["components"]["stress_tier"], -r["components"]["independent_breadth"], -r["components"]["receiver_relevance"], -r["components"]["observation_eligibility"], -r["components"]["evidence_quality"], r["market_id"], r["event_id"]))
    rows = []
    for rank, row in enumerate(scored, start=1):
        components = {
            name: {"value": row["components"][name],
                   "explanation_en": _COMPONENT_EXPLANATIONS[name][0],
                   "explanation_zh": _COMPONENT_EXPLANATIONS[name][1]}
            for name in _COMPONENT_NAMES}
        rows.append({"rank": rank, "market_id": row["market_id"],
                     "event_id": row["event_id"], "components": components,
                     "ordering_rule": ORDERING_RULE})
    return rows


def summarize_event(event) -> dict:
    """Closed-template bilingual summary; no free prose anywhere."""
    doc = load_channels()
    labels = _pathway_labels(doc)
    edges = event.get("channel_evidence") or []
    seen: list[str] = []
    for edge in edges:
        if edge["pathway"] not in seen:
            seen.append(edge["pathway"])
    if seen:
        pathways_en = "; ".join(
            f"{labels[p][0]} ({e['channel']})"
            for p, e in zip(seen,
                            [next(e for e in edges if e["pathway"] == p)
                             for p in seen]))
        pathways_zh = "；".join(
            f"{labels[p][1]}（{e['channel']}）"
            for p, e in zip(seen,
                            [next(e for e in edges if e["pathway"] == p)
                             for p in seen]))
    else:
        pathways_en = pathways_zh = "none"
    common_status = next(
        (a["status"] for a in event.get("alternative_explanations") or []
         if a.get("id") == "common_global_shock"), "live")
    template_en, template_zh = _SUMMARY_TEMPLATES[
        (event["us_response_stage"], event["attribution"])]
    return {
        "contract_version": CONTRACT_VERSION,
        "event_id": event["event_id"],
        "origin_market": event["origin"]["market_id"],
        "us_response_stage": event["us_response_stage"],
        "attribution": event["attribution"],
        "alternative_explanations": [
            {"id": a["id"], "status": a["status"]}
            for a in event.get("alternative_explanations") or []],
        "edges": [{"edge_id": e["edge_id"], "channel": e["channel"],
                   "pathway": e["pathway"],
                   "pathway_label_en": e["pathway_label_en"],
                   "pathway_label_zh": e["pathway_label_zh"],
                   "model_status": e["model_status"]}
                  for e in edges],
        "summary_en": template_en.format(pathways_en=pathways_en,
                                         cs=common_status),
        "summary_zh": template_zh.format(pathways_zh=pathways_zh,
                                         cs=common_status),
    }


def validate_summary(summary, event) -> None:
    """Reject any summary that drifts from its event or uses causal language."""
    if not isinstance(summary, dict) or tuple(summary) != _SUMMARY_KEYS:
        raise TransmissionError("summary_fields")
    if summary["contract_version"] != CONTRACT_VERSION:
        raise TransmissionError("summary_contract_version")
    if summary["event_id"] != event["event_id"]:
        raise TransmissionError("summary_event_id")
    if summary["origin_market"] != event["origin"]["market_id"]:
        raise TransmissionError("summary_origin")
    if summary["us_response_stage"] != event["us_response_stage"]:
        raise TransmissionError("summary_stage")
    if summary["attribution"] != event["attribution"]:
        raise TransmissionError("summary_attribution")
    if [(a["id"], a["status"]) for a in summary["alternative_explanations"]] != \
            [(a["id"], a["status"])
             for a in event["alternative_explanations"]]:
        raise TransmissionError("summary_alternatives")
    edges = event["channel_evidence"]
    if len(summary["edges"]) != len(edges):
        raise TransmissionError("summary_edge_count")
    for summary_edge, event_edge in zip(summary["edges"], edges):
        if tuple(summary_edge) != ("edge_id", "channel", "pathway",
                                   "pathway_label_en", "pathway_label_zh",
                                   "model_status"):
            raise TransmissionError("summary_edge_fields")
        if summary_edge["edge_id"] != event_edge["edge_id"]:
            raise TransmissionError("summary_edge_id")
        if summary_edge["channel"] != event_edge["channel"]:
            raise TransmissionError("summary_edge_channel")
        if summary_edge["pathway"] != event_edge["pathway"]:
            raise TransmissionError("summary_edge_pathway")
        if (summary_edge["pathway_label_en"] != event_edge["pathway_label_en"]
                or summary_edge["pathway_label_zh"]
                != event_edge["pathway_label_zh"]):
            raise TransmissionError("summary_edge_labels")
        if summary_edge["model_status"] != event_edge["model_status"]:
            raise TransmissionError("summary_edge_model_status")
    if scan_causal_language(summary):
        raise TransmissionError("summary_causal_language")


def build_board(*, market_ids, edges, observations, events, as_of,
                channels=None, universe=None) -> dict:
    """The transmission-board data document (the UI itself is another lane)."""
    doc = _channels_doc(channels)  # board: config legend + per-market summaries
    return {
        "contract_version": CONTRACT_VERSION,
        "as_of": str(as_of),
        "channels": [{"id": c["id"], "label_en": c["label_en"],
                      "label_zh": c["label_zh"],
                      "glyph_family": c["glyph_family"], "order": c["order"]}
                     for c in doc["channels"]],
        "pathways": [{"id": p["id"], "label_en": p["label_en"],
                      "label_zh": p["label_zh"]} for p in doc["pathways"]],
        "markets": [market_summary(market_id, edges=edges,
                                   observations=observations,
                                   universe=universe, channels=doc)
                    for market_id in sorted(market_ids)],
        "us_relevance": us_relevance_order(events),
    }
