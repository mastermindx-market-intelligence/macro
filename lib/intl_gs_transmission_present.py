"""Pure presenter for the INTL-GS Transmission board (IM17 -> R14 §10.4).

Contract -> display view model, and nothing else: every value on the board is
a field the merged IM17 contract emits, every withheld or missing value is a
§7 state, and no graph score, percentage of a country's exposure, beta, R-squared,
sigma, causal verb or specimen value is ever produced here. The board carries
no beta, R-squared or sigma vocabulary at all because IM17 emits none.

The future production view builder (``lib.intl_gs_transmission_view``, not in
this PR — no admitted live IM17 producer exists yet) must call
``present_transmission`` on the board document it assembles. The function is
pure and deterministic: the same payload with permuted dict insertion order
returns a canonically identical view model.
"""
from __future__ import annotations

from datetime import datetime, timezone

from engine.intl_transmission_evidence import (
    ALTERNATIVE_IDS,
    ATTRIBUTIONS,
    CHANNELS,
    COMMON_SHOCK_STATUSES,
    CONFIDENCE_LEVELS,
    CONTRACT_VERSION,
    DISPLAY_STATES,
    EVENT_ABSTAIN_REASONS,
    GLYPH_FAMILIES,
    MODEL_STATUSES,
    ORIGIN_STAGES,
    PATHWAYS,
    RESPONSE_STATUSES,
    SEVERITY_TIERS,
    US_RESPONSE_STAGES,
    TransmissionError,
    forbidden_keys,
    load_channels,
    scan_causal_language,
    validate_edge,
    validate_summary,
)

__all__ = ["PresentError", "present_transmission", "MAX_ORIGINS",
           "MAX_EDGES", "VIEW_CONTRACT", "channel_empty_strip"]


class PresentError(ValueError):
    """A payload the presenter refuses; the board never guesses."""


MAX_ORIGINS = 4
MAX_EDGES = 8
VIEW_CONTRACT = "intl-gs-transmission-view-v1"

_PAYLOAD_KEYS = {"board", "events", "summaries", "rank_strips", "selection",
                 "specimen"}

# Closed vocabularies (EN / ZH). Every id of the merged IM17 constants is
# mapped; an unknown id is refused, never guessed.
RESPONSE_WORDS = {
    "pending": ("Pending", "待定"),
    "responded_consistent": ("Responded · consistent", "已响应 · 方向一致"),
    "responded_inconsistent": ("Responded · inconsistent", "已响应 · 方向不一致"),
    "responded_direction_not_assessed": ("Responded · direction not assessed",
                                         "已响应 · 未评估方向"),
    "absent": ("Absent", "未响应"),
    "ineligible": ("Ineligible window", "窗口不合格"),
    "unavailable": ("Unavailable", "不可用"),
}
STAGE_WORDS = {
    "pending": ("Pending", "待定"),
    "absent": ("Absent", "未见响应"),
    "mixed": ("Mixed", "混合"),
    "corroborating": ("Corroborating", "相互印证"),
    "not_assessed": ("Not assessed", "未评估"),
}
ATTRIBUTION_WORDS = {
    "common_global_shock_favored": ("Common global shock favoured",
                                    "倾向于全球共同冲击"),
    "bilateral_channel_candidate": ("Bilateral channel candidate",
                                    "双边渠道候选"),
    "undetermined": ("Undetermined", "未确定"),
}
COMMON_WORDS = {
    "favored": ("Favoured", "倾向"),
    "live": ("Live", "仍然成立"),
    "not_indicated": ("Not indicated", "未显示"),
}
CONFIDENCE_WORDS = {
    "insufficient": ("Insufficient", "不足"),
    "single_family": ("Single evidence family", "单一证据族"),
    "independent_families": ("Independent evidence families", "独立证据族"),
}
ORIGIN_STAGE_WORDS = {
    "local_stress": ("Local stress", "本地压力"),
    "regional_spread_candidate": ("Regional spread candidate", "区域扩散候选"),
}
SEVERITY_WORDS = {
    "none": ("None", "无"),
    "within_reference_range": ("Within reference range", "处于参考区间内"),
    "outside_reference_range": ("Outside reference range", "超出参考区间"),
    "outside_reference_range_persistent": ("Outside reference range · persistent",
                                           "超出参考区间 · 持续"),
}
STRUCTURAL_WORDS = {
    "member": ("In structural graph", "在结构图内"),
    "outside_structural_graph": ("Outside structural graph", "在结构图外"),
}
REASON_WORDS = {
    "origin_not_qualified": ("Origin not qualified", "源头未合格"),
    "origin_is_receiver": ("Origin is the receiver", "源头即接收方"),
    "clock_missing": ("Clock missing", "缺少时钟"),
    "clock_order_violation": ("Clock order violation", "时钟顺序违规"),
    "stress_unqualified": ("Stress unqualified", "压力未合格"),
    "no_receiver_sessions": ("No receiver sessions", "无接收方交易时段"),
}
MODEL_STATUS_WORDS = {
    "observed_qualified": ("Observed, qualified", "已观测，合格"),
    "documented_source": ("Documented source", "有记录来源"),
    "statistical_estimate_frozen": ("Frozen statistical estimate", "冻结的统计估计"),
    "research_candidate_unpromoted": ("Research candidate, not promoted",
                                      "研究候选，未晋级"),
    "structural_prior_frozen": ("Frozen structural prior", "冻结的结构先验"),
    "scenario_assumption": ("Scenario assumption", "情景假设"),
}
AUTHORITY_WORDS = {
    "rights_matrix": ("Rights matrix row", "权利矩阵行"),
    "no_rights_row": ("No rights row", "无权利行"),
    "house_model": ("House model", "内部模型"),
}
RANK_REASON_WORDS = {
    "no_admitted_source": ("No admitted source", "无获准来源"),
    "no_rights_row": ("No rights row", "无权利行"),
    "rights_unresolved": ("Rights unresolved", "权利未决"),
    "no_qualified_value": ("No qualified value", "无合格数值"),
}
SECTION_WORDS = {
    "qualified_observations": ("Qualified observations", "合格观测"),
    "structural_research": ("Structural research", "结构性研究"),
    "statistical_evidence": ("Statistical evidence", "统计证据"),
    "structural_graph": ("Structural graph", "结构图"),
}
COMPONENT_WORDS = {
    "stress_tier": ("Stress tier", "压力档位"),
    "independent_breadth": ("Independent breadth", "独立广度"),
    "receiver_relevance": ("Receiver relevance", "接收方相关度"),
    "observation_eligibility": ("Observation eligibility", "观测合格性"),
    "evidence_quality": ("Evidence quality", "证据质量"),
}
_DIRECTION_EN = {"up": "Expected up", "down": "Expected down"}
_DIRECTION_ZH = {"up": "预期上行", "down": "预期下行"}
_SUPPORT_EN = {"documented": "documented",
               "statistical_candidate": "directional candidate"}
_SUPPORT_ZH = {"documented": "有文献支持",
               "statistical_candidate": "方向候选"}

# Graph geometry (px, inside the view box): origin node, receiver column and
# the vertical step that separates multiple edges between the same pair.
_VIEW_BOX = "0 0 880 300"
_ORIGIN_X, _ORIGIN_Y = 110, 150
_RECEIVER_X = 770
_RECEIVER_Y = (60, 150, 240)
_EDGE_STEP = 26
_TRACK_W = 200

_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_NONE_CLOCK = {"en": "—", "zh": "—"}


def _words(table, name, key):
    try:
        return table[key]
    except (KeyError, TypeError):
        raise PresentError(f"vocab:{name}:{key}") from None


def _pair(table, name, key, **extra):
    en, zh = _words(table, name, key)
    return {"en": en, "zh": zh, **extra}


def _parse_instant(text):
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:  # a naive value is UTC
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _clock(text):
    """§5 clock: EN '21 Oct 08:00 UTC' / ZH '10月21日 08:00 UTC'; a bare date
    renders without a time; None renders the em dash."""
    moment = _parse_instant(text)
    if moment is None:
        return dict(_NONE_CLOCK)
    date_only = "T" not in str(text) and ":" not in str(text)
    zh_date = f"{moment.month}月{moment.day}日"
    if date_only:
        return {"en": f"{moment.day} {_MONTHS_EN[moment.month - 1]} {moment.year}",
                "zh": f"{moment.year}年{zh_date}"}
    stamp = moment.strftime("%H:%M")
    return {"en": f"{moment.day} {_MONTHS_EN[moment.month - 1]} {stamp} UTC",
            "zh": f"{zh_date} {stamp} UTC"}


def _range_clock(start_text, end_text):
    """§5 clock RANGE: same UTC date joins the times; different dates repeat
    the day on both sides."""
    start, end = _parse_instant(start_text), _parse_instant(end_text)
    if start is None or end is None:
        return dict(_NONE_CLOCK)
    stamp_a, stamp_b = start.strftime("%H:%M"), end.strftime("%H:%M")
    if start.date() == end.date():
        month = _MONTHS_EN[start.month - 1]
        return {"en": f"{start.day} {month} {stamp_a}–{stamp_b} UTC",
                "zh": f"{start.month}月{start.day}日 {stamp_a}–{stamp_b} UTC"}
    month_a, month_b = _MONTHS_EN[start.month - 1], _MONTHS_EN[end.month - 1]
    return {"en": (f"{start.day} {month_a} {stamp_a}"
                   f" – {end.day} {month_b} {stamp_b} UTC"),
            "zh": (f"{start.month}月{start.day}日 {stamp_a}"
                   f" – {end.month}月{end.day}日 {stamp_b} UTC")}


def _numeral_text(value):
    """The numeral string at the source's own precision; never re-scaled."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, None
    text = f"{value:g}"
    decimals = len(text.split(".")[1]) if "." in text else 0
    return text, decimals


def _legend(doc):
    receivers = doc["receivers"]
    drawable = [c for c in doc["channels"] if c["id"] != "common_global_shock"]
    rows = []
    for family in doc["glyph_families"]:
        rows.append({
            "glyph_family": family["id"],
            "type_en": family["label_en"], "type_zh": family["label_zh"],
            "channels": [{"channel": c["id"], "label_en": c["label_en"],
                          "label_zh": c["label_zh"]}
                         for c in drawable if c["glyph_family"] == family["id"]],
        })
    common = next(c for c in doc["channels"]
                  if c["id"] == "common_global_shock")
    return rows, {
        "label_en": common["label_en"], "label_zh": common["label_zh"],
        "note_en": ("Not drawn as an edge: always listed as an alternative "
                    "explanation"),
        "note_zh": "不作为传导边绘制：始终列为替代解释",
    }, receivers


def _tier(source):
    if not source["emission_permitted"]:
        return {"kind": "restricted", "en": "Restricted", "zh": "受限"}
    if source["authority"] == "house_model":
        return {"kind": "house_model", "en": "House model", "zh": "内部模型"}
    return {"kind": "rights_cleared", "en": "Rights cleared", "zh": "权利已确认"}


def _expected_words(direction):
    if direction is None or direction["support"] == "unsupported":
        return {"en": "No expected direction", "zh": "无预期方向"}
    way = direction["expected_receiver_direction"]
    return {"en": (f"{_DIRECTION_EN[way]} · "
                   f"{_SUPPORT_EN[direction['support']]}"),
            "zh": (f"{_DIRECTION_ZH[way]} · "
                   f"{_SUPPORT_ZH[direction['support']]}")}


def _graph(origin_label, receivers_cfg, edges, abstained):
    doc = load_channels()
    families = {f["id"]: f for f in doc["glyph_families"]}
    receivers = [{"receiver_id": r["id"], "x": _RECEIVER_X,
                  "y": _RECEIVER_Y[index],
                  "label_en": r["label_en"], "label_zh": r["label_zh"]}
                 for index, r in enumerate(receivers_cfg)]
    receiver_y = {r["receiver_id"]: r["y"] for r in receivers}
    receiver_label = {r["receiver_id"]: (r["label_en"], r["label_zh"])
                      for r in receivers}
    origin = {"x": _ORIGIN_X, "y": _ORIGIN_Y,
              "label_en": origin_label[0], "label_zh": origin_label[1]}
    mid_x = (_ORIGIN_X + _RECEIVER_X) // 2
    drawn, per_pair = [], {}
    for edge in edges:
        pair = edge["receiver"]
        k = per_pair.get(pair, 0)
        per_pair[pair] = k + 1
        offset = 0 if k == 0 else k * _EDGE_STEP * (1 if k % 2 else -1)
        end_y = receiver_y[pair]
        control_y = (_ORIGIN_Y + end_y) // 2 + offset
        path = (f"M {_ORIGIN_X} {_ORIGIN_Y} "
                f"Q {mid_x} {control_y} {_RECEIVER_X} {end_y}")
        label_y = (_ORIGIN_Y + 2 * control_y + end_y) // 4
        drawn.append({
            "e": edge["e"], "edge_id": edge["edge_id"],
            "glyph_family": edge["glyph_family"], "d": path,
            "label_x": mid_x, "label_y": label_y,
            "label_en": (f"{edge['channel']['label_en']} · "
                         f"{edge['pathway']['label_en']}"),
            "label_zh": (f"{edge['channel']['label_zh']} · "
                         f"{edge['pathway']['label_zh']}"),
        })
    if abstained:
        aria_en, aria_zh = "No qualified transmission event.", "无合格传导事件。"
    else:
        sentences, sentences_zh = [], []
        for receiver in receivers:
            rid = receiver["receiver_id"]
            phrases = [f"{families[e['glyph_family']]['label_en']} channel, "
                       f"{e['pathway']['label_en']}"
                       for e in edges if e["receiver"] == rid]
            phrases_zh = [f"{families[e['glyph_family']]['label_zh']}渠道，"
                          f"{e['pathway']['label_zh']}"
                          for e in edges if e["receiver"] == rid]
            if not phrases:
                continue
            sentences.append(f"{origin_label[0]} to "
                             f"{receiver_label[rid][0]}: "
                             f"{'; '.join(phrases)}.")
            sentences_zh.append(f"{origin_label[0]}至"
                                f"{receiver_label[rid][1]}："
                                f"{'；'.join(phrases_zh)}。")
        aria_en, aria_zh = " ".join(sentences), " ".join(sentences_zh)
    return {"view_box": _VIEW_BOX, "origin": origin, "receivers": receivers,
            "edges": drawn, "aria_en": aria_en, "aria_zh": aria_zh}


def _rank_rows(strip, doc):
    channels = {c["id"]: c for c in doc["channels"]}
    rows = []
    for raw in strip:
        channel = channels[raw["channel"]]
        row = {
            "channel": raw["channel"],
            "label_en": channel["label_en"], "label_zh": channel["label_zh"],
            "glyph_family": raw["glyph_family"], "state": raw["state"],
            "reason": (_pair(RANK_REASON_WORDS, "rank_reason", raw["reason"])
                       if raw["reason"] else None),
            "value_text": None, "value": None, "dp": None,
            "units": raw["units"], "denominator": raw["denominator"],
            "as_of": _clock(raw["as_of"]), "source_id": raw["source_id"],
            "rank": raw["rank"], "rank_population": raw["rank_population"],
            "tick_x": None, "ticks": None,
        }
        if raw["state"] == "shown":
            text, decimals = _numeral_text(raw["value"])
            population = raw["rank_population"] or 1
            rank = raw["rank"] or 1
            if population <= 1:
                tick_x, ticks = _TRACK_W, [{"rank": rank, "x": _TRACK_W}]
            else:
                tick_x = int(round(
                    _TRACK_W * (population - rank) / (population - 1)))
                ticks = [{"rank": 1, "x": _TRACK_W},
                         {"rank": population, "x": 0}]
            row.update({"value_text": text, "value": raw["value"],
                        "dp": decimals, "tick_x": tick_x, "ticks": ticks})
        rows.append(row)
    return rows


def _edge_view(flat, index, receivers_by_id, receiver_labels):
    edge_id = flat["edge_id"]
    display = flat["value"]["display"]
    if display not in DISPLAY_STATES:
        raise PresentError(f"edge_invalid:{edge_id}")
    receiver = receivers_by_id.get(flat["receiver"])
    window = (receiver or {}).get("window") or {}
    response = (receiver or {}).get("response") or {}
    status = response.get("status", "unavailable")
    value_text = None
    if display == "shown":
        text, _decimals = _numeral_text(flat["value"]["amount"])
        value_text = (f"{text} {flat['units']} · "
                      f"{flat['value']['denominator']}")
    label_en, label_zh = receiver_labels.get(
        flat["receiver"], (flat["receiver"], flat["receiver"]))
    return {
        "e": index, "n": index + 1, "edge_id": edge_id,
        "name_en": f"{flat['origin_market']} → {label_en}",
        "name_zh": f"{flat['origin_market']} → {label_zh}",
        "glyph_family": flat["glyph_family"],
        "type_en": flat["type_en"], "type_zh": flat["type_zh"],
        "receiver_id": flat["receiver"],
        "channel": {"id": flat["channel"],
                    "label_en": flat["channel_label_en"],
                    "label_zh": flat["channel_label_zh"]},
        "pathway": {"id": flat["pathway"],
                    "label_en": flat["pathway_label_en"],
                    "label_zh": flat["pathway_label_zh"]},
        "model_status": {"id": flat["model_status"], **_pair(
            MODEL_STATUS_WORDS, "model_status", flat["model_status"])},
        "evidence_family": flat["evidence_family"],
        "mechanism": {"en": flat["interpretation_en"],
                      "zh": flat["interpretation_zh"]},
        "evidence": {"en": (f"{_words(MODEL_STATUS_WORDS, 'model_status', flat['model_status'])[0]} · "
                            f"{_words(AUTHORITY_WORDS, 'authority', flat['source']['authority'])[0]}"),
                     "zh": (f"{_words(MODEL_STATUS_WORDS, 'model_status', flat['model_status'])[1]} · "
                            f"{_words(AUTHORITY_WORDS, 'authority', flat['source']['authority'])[1]}")},
        "window": {**_range_clock(window.get("start"), window.get("end")),
                   "same_session": window.get("same_session_as_knowable"),
                   "state": window.get("state"),
                   "reason": (_pair(REASON_WORDS, "reason", window["reason"])
                              if window.get("state") == "abstain"
                              and window.get("reason") else None)},
        "expected": _expected_words(flat["direction"]),
        "observed": {"status": status, **_pair(
            RESPONSE_WORDS, "response", status)},
        "tier": _tier(flat["source"]),
        "value": {"display": display, "text": value_text,
                  "units": flat["units"],
                  "denominator": flat["value"]["denominator"],
                  "as_of": _clock(flat["vintage"]["as_of"])},
        "source": {"source_id": flat["source"]["source_id"],
                   "authority": flat["source"]["authority"],
                   "rights_class": flat["source"]["rights_class"],
                   "rights_ref": flat["source"]["rights_ref"]},
        "vintage": {"as_of": _clock(flat["vintage"]["as_of"]),
                    "published_at": _clock(flat["vintage"]["published_at"])},
        "coverage": {"state": flat["coverage"]["state"],
                     "basis": flat["coverage"]["basis"]},
    }


def _alternatives(event):
    labelled = {"common_global_shock": ("Common global shock", "共同全球冲击"),
                "receiver_idiosyncratic": ("Receiver idiosyncratic",
                                           "接收方特质")}
    present = {a["id"]: a for a in event.get("alternative_explanations") or []}
    rows = []
    for alt_id in ALTERNATIVE_IDS:
        alt = present.get(alt_id)
        if alt is None:
            continue
        if alt_id == "common_global_shock":
            status = _pair(COMMON_WORDS, "common", alt["status"])
        else:
            status = {"en": "Live", "zh": "仍然成立"}
        rows.append({"id": alt_id, "status": alt["status"],
                     "label_en": labelled[alt_id][0],
                     "label_zh": labelled[alt_id][1],
                     "status_en": status["en"], "status_zh": status["zh"],
                     "basis_en": alt.get("basis_en", ""),
                     "basis_zh": alt.get("basis_zh", "")})
    return rows


def _origin_view(row, event, summary, strip, doc, receivers_cfg):
    market_id = row["market_id"]
    abstained = event["state"] == "abstain"
    receivers_by_id = {r["receiver_id"]: r
                       for r in event.get("receivers") or []}
    receiver_labels = {r["id"]: (r["label_en"], r["label_zh"])
                       for r in receivers_cfg}

    channel_labels = {c["id"]: (c["label_en"], c["label_zh"])
                      for c in doc["channels"]}
    family_labels = {f["id"]: (f["label_en"], f["label_zh"])
                     for f in doc["glyph_families"]}
    flat_edges = []
    for index, edge in enumerate(event.get("channel_evidence") or []):
        flat = dict(edge)
        flat["e"] = index
        flat["type_en"], flat["type_zh"] = family_labels[edge["glyph_family"]]
        (flat["channel_label_en"],
         flat["channel_label_zh"]) = channel_labels[edge["channel"]]
        flat_edges.append(flat)

    edges = [_edge_view(flat, flat["e"], receivers_by_id, receiver_labels)
             for flat in flat_edges[:MAX_EDGES]]
    more_edge_ids = [flat["edge_id"] for flat in flat_edges[MAX_EDGES:]]

    pathway_labels = {p["id"]: (p["label_en"], p["label_zh"])
                      for p in doc["pathways"]}
    by_pathway = [{"pathway": pathway,
                   "label_en": pathway_labels[pathway][0],
                   "label_zh": pathway_labels[pathway][1],
                   "count": count}
                  for pathway, count
                  in (event["coverage"]["by_pathway"] or {}).items()]

    if abstained:
        desk = {"en": event["language_ceiling_en"],
                "zh": event["language_ceiling_zh"]}
    else:
        desk = {"en": summary["summary_en"], "zh": summary["summary_zh"]}

    graph = _graph(
        (market_id, market_id), receivers_cfg,
        [{"e": e["e"], "edge_id": e["edge_id"],
          "glyph_family": e["glyph_family"], "receiver": e["receiver_id"],
          "channel": e["channel"], "pathway": e["pathway"]}
         for e in edges], abstained)

    receiver_rows = []
    for cfg in receivers_cfg:
        rid = cfg["id"]
        receiver = receivers_by_id.get(rid)
        if receiver is None:
            receiver_rows.append({
                "receiver_id": rid, "label_en": receiver_labels[rid][0],
                "label_zh": receiver_labels[rid][1],
                "status": "unavailable",
                "status_en": RESPONSE_WORDS["unavailable"][0],
                "status_zh": RESPONSE_WORDS["unavailable"][1],
                "window": dict(_NONE_CLOCK), "same_session": None,
                "note": None})
            continue
        window = receiver.get("window") or {}
        response = receiver.get("response") or {}
        status = response.get("status", "unavailable")
        same_session = window.get("same_session_as_knowable")
        note = ({"en": "Not same-session testable",
                 "zh": "非同一交易时段可检验"}
                if same_session is False else None)
        receiver_rows.append({
            "receiver_id": rid, "label_en": receiver_labels[rid][0],
            "label_zh": receiver_labels[rid][1], "status": status,
            **_pair(RESPONSE_WORDS, "response", status),
            "status_en": _words(RESPONSE_WORDS, "response", status)[0],
            "status_zh": _words(RESPONSE_WORDS, "response", status)[1],
            "window": _range_clock(window.get("start"), window.get("end")),
            "same_session": same_session, "note": note})

    return {
        "i": 0, "market_id": market_id,
        "name_en": market_id, "name_zh": market_id,
        "relevance": {"rank": row["rank"], "components": [
            {"id": name, "label_en": COMPONENT_WORDS[name][0],
             "label_zh": COMPONENT_WORDS[name][1],
             "value": row["components"][name]["value"]}
            for name in COMPONENT_WORDS]},
        "event_id": event["event_id"],
        "event_state": event["state"],
        "abstain_reasons": [{"id": reason, **_pair(REASON_WORDS, "reason",
                                                  reason)}
                            for reason in event.get("abstain_reasons") or []],
        "structural": None,  # filled by the caller from the board markets
        "origin_stage": {"id": event["origin_stage"], **_pair(
            ORIGIN_STAGE_WORDS, "origin_stage", event["origin_stage"])},
        "severity": {"id": event["severity"]["tier"], **_pair(
            SEVERITY_WORDS, "severity", event["severity"]["tier"])},
        "us_response_stage": {"id": event["us_response_stage"], **_pair(
            STAGE_WORDS, "stage", event["us_response_stage"])},
        "attribution": {"id": event["attribution"], **_pair(
            ATTRIBUTION_WORDS, "attribution", event["attribution"])},
        "confidence": {"id": event["confidence"]["level"], **_pair(
            CONFIDENCE_WORDS, "confidence", event["confidence"]["level"]),
            "families": list(event["confidence"]["families"]),
            "family_count": event["confidence"]["independent_family_count"]},
        "coverage": {
            "channels_with_evidence":
                event["coverage"]["channels_with_evidence"],
            "channels_total": event["coverage"]["channels_total"],
            "by_pathway": by_pathway},
        "desk_read": desk,
        "ceiling": {"en": event["language_ceiling_en"],
                    "zh": event["language_ceiling_zh"]},
        "graph": graph,
        "rank_strip": _rank_rows(strip, doc),
        "edges": edges,
        "receivers": receiver_rows,
        "alternatives": _alternatives(event),
        "more_edges": {"count": len(more_edge_ids),
                       "edge_ids": more_edge_ids},
    }


def _market_view(market):
    structural = market["structural_graph"]
    counts = {
        "structural_research": len(market["structural_research"]),
        "qualified_observations": len(
            market["qualified_observations"]["observation_ids"]),
        "statistical_evidence": len(market["statistical_evidence"]),
        "structural_graph": 1 if structural["member"] else 0,
    }
    return {
        "market_id": market["market_id"],
        "name_en": market["market_id"], "name_zh": market["market_id"],
        "structural": {"state": structural["state"], **_pair(
            STRUCTURAL_WORDS, "structural", structural["state"])},
        "sections": [{"id": section, "en": SECTION_WORDS[section][0],
                      "zh": SECTION_WORDS[section][1],
                      "count": counts[section]}
                     for section in market["display_order"]],
    }


def channel_empty_strip(doc=None):
    """Rows for a market with no strip: the unavailable state, never a zero."""
    doc = load_channels() if doc is None else doc
    return [{"channel": c["id"], "glyph_family": c["glyph_family"],
             "state": "unavailable", "reason": "no_admitted_source",
             "measure_id": None, "units": None, "denominator": None,
             "value": None, "rank": None, "rank_population": None,
             "source_id": None, "as_of": None}
            for c in doc["channels"] if c["id"] != "common_global_shock"]


_FORBIDDEN_KEY_PARTS = ("pct", "percent", "share", "ratio", "score",
                        "centrality", "percentile")


def _causal_twin(node):
    """A scan-friendly twin of the view model: the engine scanner reads only
    ``*_en``/``*_zh`` keys, while this contract emits ``{en, zh}`` pairs, so
    every pair is lifted to ``v_en``/``v_zh`` before the scan sees it."""
    if isinstance(node, dict):
        out = {}
        for key, val in node.items():
            if key in ("en", "zh") and isinstance(val, str):
                out[f"v_{key}"] = val
            else:
                out[key] = _causal_twin(val)
        return out
    if isinstance(node, list):
        return [_causal_twin(item) for item in node]
    return node


def _self_check(output):
    leaked = forbidden_keys(output)
    if leaked:
        raise PresentError(f"output_forbidden_key:{leaked[0]}")

    def walk(node, prefix=""):
        if isinstance(node, dict):
            for key, val in node.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if any(part in str(key).lower()
                       for part in _FORBIDDEN_KEY_PARTS):
                    raise PresentError(f"output_forbidden_key:{path}")
                walk(val, path)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{prefix}.{index}" if prefix else str(index))

    walk(output)
    causal = scan_causal_language(_causal_twin(output))
    if not causal:
        causal = scan_causal_language(output)
    if causal:
        raise PresentError(f"output_causal:{causal[0]}")


_EDGE_FIELDS = ("contract_version", "edge_id", "origin_market", "receiver",
                "channel", "glyph_family", "pathway", "pathway_label_en",
                "pathway_label_zh", "model_status", "evidence_family",
                "underlying_id", "source", "vintage", "measure_id", "units",
                "interpretation_en", "interpretation_zh", "direction",
                "coverage", "revision", "value")


def _canonical_edge(edge):
    """The engine pins edge field ORDER, so a caller whose dicts differ only
    by insertion order is canonicalized here before validation — the values
    are untouched and the output is insertion-order invariant."""
    if (isinstance(edge, dict) and set(edge) == set(_EDGE_FIELDS)
            and tuple(edge) != _EDGE_FIELDS):
        return {key: edge[key] for key in _EDGE_FIELDS}
    return edge


def present_transmission(payload: dict) -> dict:
    """IM17 board document -> the §10.4 Transmission board view model."""
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise PresentError("payload_keys")
    board = payload["board"]
    events = list(payload["events"] or [])
    summaries = dict(payload["summaries"] or {})
    rank_strips = dict(payload["rank_strips"] or {})
    selection = dict(payload["selection"] or {})
    if board.get("contract_version") != CONTRACT_VERSION:
        raise PresentError("board_contract")

    events_by_id = {}
    for event in events:
        if not isinstance(event, dict):
            raise PresentError("event_contract")
        if event.get("contract_version") != CONTRACT_VERSION:
            raise PresentError("event_contract")
        events_by_id[event["event_id"]] = event
        for edge in event.get("channel_evidence") or []:
            try:
                validate_edge(_canonical_edge(edge))
            except TransmissionError:
                raise PresentError(
                    f"edge_invalid:{edge.get('edge_id', '?')}") from None

    for event_id in summaries:
        if event_id not in events_by_id:
            raise PresentError(f"summary_orphan:{event_id}")
    for event in events:
        event_id = event["event_id"]
        summary = summaries.get(event_id)
        if event["state"] != "abstain" and summary is None:
            raise PresentError(f"summary_invalid:{event_id}")
        if summary is not None:
            try:
                validate_summary(summary, event)
            except TransmissionError:
                raise PresentError(f"summary_invalid:{event_id}") from None

    rows = list(board["us_relevance"])
    row_by_market = {r["market_id"]: r for r in rows}
    origin_market = selection.get("origin_market")
    selected_event_id = selection.get("event_id")
    selected_edge_id = selection.get("edge_id")
    if origin_market is not None and origin_market not in row_by_market:
        raise PresentError("selection_unknown")
    if selected_event_id is not None and selected_event_id not in events_by_id:
        raise PresentError("selection_unknown")

    chosen_rows = rows[:MAX_ORIGINS]
    promoted = False
    if origin_market is not None:
        later = [r for r in rows[MAX_ORIGINS:]
                 if r["market_id"] == origin_market]
        if later:
            chosen_rows = rows[:MAX_ORIGINS - 1] + later[:1]
            promoted = True

    markets = {m["market_id"]: m for m in board["markets"]}
    doc = load_channels()
    legend_rows, common_legend, receivers_cfg = _legend(doc)

    origins = []
    for slot, row in enumerate(chosen_rows):
        event = events_by_id[row["event_id"]]
        summary = summaries.get(row["event_id"])
        strip = rank_strips.get(row["market_id"]) or channel_empty_strip(doc)
        origin = _origin_view(row, event, summary, strip, doc, receivers_cfg)
        origin["i"] = slot
        market = markets.get(row["market_id"])
        state = (market or {"structural_graph": {
            "state": "outside_structural_graph"}})["structural_graph"]["state"]
        origin["structural"] = {"state": state, **_pair(
            STRUCTURAL_WORDS, "structural", state)}
        origins.append(origin)

    if origin_market is None:
        selected_i = 0
    else:
        selected_i = next((slot for slot, o in enumerate(origins)
                           if o["market_id"] == origin_market), 0)
    selected_origin = origins[selected_i]
    if selected_edge_id is not None:
        edge_ids = [e["edge_id"] for e in selected_origin["edges"]]
        if selected_edge_id not in edge_ids:
            raise PresentError("selection_unknown")
        selected_e = edge_ids.index(selected_edge_id)
    else:
        selected_e = 0

    more_origins = [{"market_id": r["market_id"], "rank": r["rank"]}
                    for r in rows[len(chosen_rows):]]

    output = {
        "view_contract": VIEW_CONTRACT,
        "specimen": bool(payload["specimen"]),
        "as_of": _clock(board.get("as_of")),
        "legend": legend_rows,
        "common_shock_legend": common_legend,
        "origins": origins,
        "more_origins": more_origins,
        "selection_promoted": promoted,
        "selected": {"i": selected_i, "e": selected_e},
        "markets": [_market_view(m) for m in board["markets"]],
    }

    _self_check(output)
    return output
