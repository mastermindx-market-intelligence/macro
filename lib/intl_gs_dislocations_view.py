"""Dislocation explorer view builder (INTL-GS-W3U, packet IM15 surface).

Runs the merged IM15 engine (``engine/intl_global_dislocation.py``, read-only)
over the IM12 observation set the W2 seam already receives
(``attach_surveillance(observations=...)`` → ``build_view``) and emits one
panel payload for ``templates/intl_workspace/dislocations.html.j2``.

Honesty contract (R14 §1.3 + seat rulings R1–R4):
- every number in the payload is an engine/IM12 field or a declared geometry
  constant — nothing is invented, no specimen value ever ships in production
  (``fragility`` is passed only by the test fixture, with ``specimen=True``);
- no admitted fragility producer exists on main, so production carries
  ``fragility`` None per row and the FRAGILITY column renders the abstained
  state (ruling R1); no stance producer exists (ruling R2; the engine's
  ``attention`` label is an attention reading, never a stance);
- the ranking statistic is ``evidence.modified_z`` of
  ``dislocation_peer_divergence(kind="peer_divergence_return", basis
  usd_unhedged, peer_rule="same_universe_region")`` (ruling R3); ``computed_at``
  is the observation set's own latest computation clock, never the wall clock;
- ``DislocationError`` is never caught here — the seam turns a raising builder
  into status ``error`` for this view alone (ruling R4).

Pure module: imports only the stdlib, the IM15/IM12 engine contracts and
``lib.intl_gs_display``; no file, network, environment or clock access; the
same inputs always produce byte-identical payloads.
"""
from __future__ import annotations

import math

from engine.intl_global_dislocation import (
    ATTENTION_MODIFIED_Z,
    DISLOCATION_ABSTAIN_REASONS,
    EXCLUSION_REASONS,
    dislocation_own_history,
    dislocation_peer_divergence,
    region_of,
)
from lib.intl_gs_display import (
    NAMES_ZH,
    format_clock,
    horizon_label,
    reason_copy,
)

#: Ruling R1: the R14 board's 0–100 fragility score has no admitted producer.
#: 60 is the labelled threshold of the *layout*, not an engine output.
FRAGILITY_THRESHOLD = 60

#: Ruling R3: exclusions that make an otherwise qualified receipt "Qualified"
#: (partial evidence) rather than Complete in the §7 view grammar.
_QUALIFYING_EXCLUSIONS = ("not_qualified", "not_point_in_time",
                          "fx_leg_unavailable", "window_end_mismatch")

#: §10.3 scatter geometry (viewBox 0 0 640 420): plot box, scales, clamp.
_SCATTER_X0, _SCATTER_X1 = 64.0, 616.0
_SCATTER_Y0, _SCATTER_Y1 = 24.0, 364.0
_SCATTER_Y_MID = 194.0
_FRAGILITY_SPAN = 100.0
_Z_SPAN = 7.0
_PX_PER_Z = (_SCATTER_Y1 - _SCATTER_Y0) / 2.0 / _Z_SPAN  # 24.2857 px per z
_PX_PER_FRAGILITY = (_SCATTER_X1 - _SCATTER_X0) / _FRAGILITY_SPAN  # 5.52

#: Display cap of the ranking table (§10.3 board shows seven; the cap keeps
#: the radio/CSS contract bounded at indices 0..11).
RANK_CAP = 12

#: (en, zh) for every IM15 abstain/exclusion token the engine can emit, plus
#: the W3U display token for the unproduced fragility score. The key set is
#: asserted equal to the engine vocabulary by tests (V7), so a new engine token
#: fails the suite instead of rendering raw.
DISLOCATION_REASON_COPY = {
    # --- engine.intl_global_dislocation.DISLOCATION_ABSTAIN_REASONS ---
    "subject_not_qualified": ("Subject not qualified", "主体未获资格"),
    "subject_fx_leg_unavailable": ("Subject FX leg unavailable", "主体汇率腿不可用"),
    "insufficient_reference_history": ("Insufficient reference history", "参考历史不足"),
    "insufficient_peers": ("Insufficient peers", "同组市场不足"),
    "dispersion_degenerate": ("Degenerate peer dispersion", "同组离散度退化"),
    "subject_block_incomplete": ("Subject block incomplete", "主体窗口块不完整"),
    "peer_group_unresolved": ("Peer group unresolved", "同组无法解析"),
    "clock_missing": reason_copy("clock_missing"),
    "clock_order_violation": reason_copy("clock_order_violation"),
    # --- engine.intl_global_dislocation.EXCLUSION_REASONS ---
    "not_qualified": ("Peer not qualified", "同组市场未获资格"),
    "market_mismatch": ("Market mismatch", "市场不匹配"),
    "subject_market": ("Subject market", "主体市场"),
    "horizon_mismatch": ("Horizon mismatch", "区间不匹配"),
    "window_end_mismatch": ("Window end mismatch", "窗口末端不匹配"),
    "not_point_in_time": ("Not point-in-time", "非时点数据"),
    "fx_leg_unavailable": ("FX leg unavailable", "汇率腿不可用"),
    "outside_peer_group": ("Outside peer group", "同组之外"),
    "window_overlap": ("Window overlap", "窗口重叠"),
    "duplicate_window": ("Duplicate window", "重复窗口"),
    "block_not_contiguous": ("Block not contiguous", "窗口块不连续"),
    # --- W3U display token (ruling R1) ---
    "fragility_unadmitted": ("No admitted fragility score", "无已准入的脆弱度评分"),
}

#: (en, zh) for the universe region tokens (engine peer groups).
REGION_COPY = {
    "asia_pacific": ("Asia-Pacific", "亚太"),
    "europe": ("Europe", "欧洲"),
    "middle_east_africa": ("Middle East & Africa", "中东及非洲"),
    "americas": ("Americas", "美洲"),
}

#: Every user-visible string the template renders, as {en, zh} pairs; the
#: template never invents copy.
COPY = {
    "title": ("Dislocation explorer", "错位探索"),
    "qnum": ("Q2", "Q2"),
    "scatter_title": ("Q2 dislocation map", "Q2 错位图"),
    "x_axis_title": ("Fragility score (0–100)", "脆弱度评分（0–100）"),
    "y_axis_title": ("Modified z (robust, MAD)", "修正z值（稳健，MAD）"),
    "threshold_label": ("Fragility threshold 60", "脆弱度阈值 60"),
    "attention_ticks": ("±3.5 attention", "±3.5 关注阈值"),
    "not_plotted": ("Not plotted", "未绘制"),
    "scatter_empty_note": ("No admitted fragility score — nothing to plot",
                           "无已准入的脆弱度评分——暂无可绘制数据"),
    "scatter_aria": ("Dislocation map: fragility score on the horizontal axis "
                     "against modified z (robust, MAD) on the vertical axis; the "
                     "dashed line marks the fragility threshold at 60.",
                     "错位图：横轴为脆弱度评分，纵轴为修正z值（稳健，MAD）；虚线标记脆弱度阈值 60。"),
    "vh_market": ("Market", "市场"),
    "vh_fragility": ("Fragility", "脆弱度"),
    "vh_z": ("Modified z", "修正z值"),
    "peers_suffix": ("peers", "同组市场"),
    "peers_title_none": ("Peers", "同组市场"),
    "region_asia_pacific": REGION_COPY["asia_pacific"],
    "region_europe": REGION_COPY["europe"],
    "region_middle_east_africa": REGION_COPY["middle_east_africa"],
    "region_americas": REGION_COPY["americas"],
    "attention_outside": ("Outside reference range", "参考范围之外"),
    "attention_within": ("Within reference range", "参考范围之内"),
    "fragility_reason": DISLOCATION_REASON_COPY["fragility_unadmitted"],
    "stance_reason": reason_copy("stance_unadmitted"),
    "common_reason": reason_copy("common_factor_unadmitted"),
    "peers_counts": ("{used} used · {offered} offered", "已用 {used} · 提供 {offered}"),
    "peers_empty": ("No qualified peers for this market", "该市场无合格同组"),
    "ranking_title": ("Divergence ranking", "背离排名"),
    "ranking_sub": ("{ranked} ranked · {unranked} unranked · {carried} carried",
                    "已排名 {ranked} · 未排名 {unranked} · 载入 {carried}"),
    "header_rank": ("#", "#"),
    "header_market": ("MARKET", "市场"),
    "header_residual": ("DOWN ◀ RESIDUAL ▶ UP", "下 ◀ 残差 ▶ 上"),
    "header_z": ("Z", "Z"),
    "header_usd": ("USD", "美元%"),
    "header_local": ("LOCAL", "本币%"),
    "header_fx": ("FX", "汇率%"),
    "header_fragility": ("FRAGILITY", "脆弱度"),
    "header_state": ("DATA STATE", "数据状态"),
    "header_stance": ("STANCE", "立场"),
    "above_threshold": ("above threshold", "高于阈值"),
    "empty_census": ("No qualified dislocation", "无合格背离"),
    "insp_title": ("Selected market", "选中市场"),
    "insp_market": ("Market", "市场"),
    "insp_region": ("Region", "地区"),
    "insp_horizon": ("Horizon", "区间"),
    "insp_basis": ("Basis", "口径"),
    "basis_value": ("USD · Unhedged", "美元 · 未对冲"),
    "clock_observation": ("Reference period", "参考区间"),
    "clock_source": ("Source available", "来源可得"),
    "clock_ingestion": ("Acquired + qualified", "采集并合格"),
    "clock_computation": ("Published", "发布"),
    "insp_state": ("State", "状态"),
    "insp_z": ("Modified z", "修正z值"),
    "insp_attention": ("Attention", "关注"),
    "rank_text_above": ("Higher than {below} of {n} peers",
                        "高于 {n} 个同组市场中的 {below} 个"),
    "rank_text_below": ("Lower than {above} of {n} peers",
                        "低于 {n} 个同组市场中的 {above} 个"),
    "decompose_title": ("Return decomposition", "回报分解"),
    "leg_local": ("Local", "本币"),
    "leg_fx": ("FX", "汇率"),
    "leg_cross": ("Cross term", "交叉项"),
    "leg_total": ("Total USD", "美元合计"),
    "leg_common": ("Common factor", "共同因子"),
    "drivers_title": ("Fragility drivers", "脆弱度驱动"),
    "drivers_empty": ("No admitted fragility drivers", "无已准入的脆弱度驱动"),
    "extras_title": ("Other engine readings", "其他引擎读数"),
    "extra_all": ("All-qualified peers z", "全部合格同组 z"),
    "extra_local": ("Local-basis z", "本币口径 z"),
    "extra_fx": ("FX-leg z", "汇率腿 z"),
    "extra_own": ("Own history", "自身历史"),
    "summary_title": ("Q3–Q6 summary", "Q3–Q6 摘要"),
    "summary_q3": ("Credit, funding, liquidity?", "信用、融资、流动性？"),
    "summary_q4": ("Transmission into the US?", "如何传导至美国？"),
    "summary_q5": ("Eligible US corroboration?", "合格的美国佐证？"),
    "summary_q6": ("What resolves the thesis?", "什么能验证或推翻论点？"),
    "summary_a3": ("Credit and funding sources not admitted", "信用与融资数据源未准入"),
    "summary_a4": ("Transmission channels not admitted — see the Transmission view",
                   "传导渠道未准入——见传导视图"),
    "summary_a5": ("US corroboration not admitted", "美国佐证未准入"),
    "summary_a6": ("No admitted thesis — see the Scenario lab", "无已准入论点——见情景实验室"),
    "btn_coverage": ("Open coverage", "打开覆盖"),
    "btn_transmission": ("Open transmission", "打开传导"),
    "btn_disabled_title": ("Target view not available in this build",
                           "目标视图在本构建中不可用"),
    "pick_aria": ("Select {market}", "选择 {market}"),
    "footnote_coverage": ("{n} universe markets have no observation for this "
                          "horizon (see Coverage).",
                          "{n} 个全球市场在该区间无观测（见覆盖视图）。"),
    "footnote_cap": ("{n} more qualified markets not ranked (display cap 12)",
                     "另有 {n} 个合格市场未排名（显示上限 12）"),
    "footnote_withheld": ("Observation set withheld — every market abstains until "
                          "the nightly publication is admitted",
                          "观测集暂扣留——在夜间发布获得准入之前，所有市场弃权。"),
}


def _reason_pair(token: str):
    """Resolved (en, zh) for a reason token: W3U copy first, then the shared
    display vocabulary; an unknown token keeps its raw text (never dropped)."""
    if token in DISLOCATION_REASON_COPY:
        return DISLOCATION_REASON_COPY[token]
    return reason_copy(token)


def _reason_entry(token: str, count=None) -> dict:
    en, zh = _reason_pair(token)
    return {"token": token, "count": count, "text": {"en": en, "zh": zh}}


def _identity(observation: dict) -> dict:
    identity = observation.get("identity") if isinstance(observation, dict) else None
    return identity if isinstance(identity, dict) else {}


def _finite(value):
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _fragility_of(fragility, market_id):
    """The fixture-only 0–100 fragility map, guarded to honest values."""
    if not isinstance(fragility, dict):
        return None
    value = _finite(fragility.get(market_id))
    if value is None or not 0.0 <= value <= 100.0:
        return None
    return value


def _horizon(workspace: dict, usd_entries: list) -> "str | None":
    """H: the declared default when carried, else the first carried config
    horizon; 'ytd' is never eligible (spec R14 horizons are windowed)."""
    config = (workspace or {}).get("config") or {}
    carried = {_identity(entry).get("horizon") for entry in usd_entries}
    default = config.get("default_horizon")
    if default is not None and default in carried and default != "ytd":
        return default
    for horizon in config.get("horizons") or []:
        if horizon != "ytd" and horizon in carried:
            return horizon
    return None


def _latest_computation(entries: list) -> "str | None":
    """Latest clocks.computation.at compared as instants (engine _as_instant
    semantics: ISO-8601, naive = UTC); never the wall clock."""
    best_text, best_moment = None, None
    for entry in entries:
        clock = (entry.get("clocks") or {}).get("computation")
        text = clock.get("at") if isinstance(clock, dict) else None
        if not isinstance(text, str) or not text:
            continue
        moment = _parse_instant(text)
        if moment is not None and (best_moment is None or moment > best_moment):
            best_text, best_moment = text, moment
    return best_text


def _parse_instant(text: str):
    from datetime import datetime, timezone
    try:
        moment = datetime.fromisoformat(str(text).strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _market_names(universe: dict, market_id: str):
    jurisdictions = (universe or {}).get("jurisdictions") or {}
    holder = jurisdictions.get(market_id) or ((universe or {}).get("aggregates") or {}).get(market_id)
    if isinstance(holder, dict) and isinstance(holder.get("name"), str) and holder["name"]:
        name_en = holder["name"]
    else:
        name_en = market_id
    return name_en, NAMES_ZH.get(market_id, name_en)


def _rankable(row: dict) -> bool:
    """A qualified rank receipt with a dislocation id, four complete clocks
    and a finite z (mutant 5: anything less renders unranked)."""
    if row.get("state") != "qualified" or not row.get("dislocation_id"):
        return False
    if _finite(row.get("z")) is None:
        return False
    clocks = row.get("clocks") or {}
    for name in ("observation", "source_publication", "ingestion", "computation"):
        clock = clocks.get(name)
        if not (isinstance(clock, dict) and isinstance(clock.get("at"), str)
                and clock.get("at")):
            return False
    return True


def rank_rows(rows: list):
    """Pure (ranked, unranked): rankable rows ordered by |z| descending
    (market_id tie-break), capped at RANK_CAP with index 0..N-1; everything
    else unranked (index None), sorted by market_id."""
    def sort_key(row: dict):
        return (-abs(_finite(row.get("z")) or 0.0), row.get("market_id") or "")

    candidates = sorted((row for row in rows if _rankable(row)), key=sort_key)
    ranked = [dict(row, index=index)
              for index, row in enumerate(candidates[:RANK_CAP])]
    rest = [row for row in rows if not _rankable(row)]
    rest.extend(candidates[RANK_CAP:])
    unranked = [dict(row, index=None)
                for row in sorted(rest, key=lambda row: row.get("market_id") or "")]
    return ranked, unranked


def _view_state(observation_reasons, receipt: dict):
    """§7 precedence for one row: Restricted > Abstain > Qualified > Complete."""
    if "rights_unconfirmed" in observation_reasons:
        return "restricted", [_reason_entry("rights_unconfirmed")]
    if receipt.get("state") == "abstain":
        return "abstain", [_reason_entry(token)
                           for token in receipt.get("abstain_reasons") or []]
    excluded = (receipt.get("references") or {}).get("excluded_by_reason") or {}
    counts = [(token, excluded.get(token) or 0) for token in _QUALIFYING_EXCLUSIONS]
    counted = [(token, n) for token, n in counts if n > 0]
    if counted:
        return "qualified", [_reason_entry(token, n) for token, n in counted]
    return "complete", []


def _extra(receipt: "dict | None", empty=False) -> dict:
    if empty or receipt is None:
        return {"state": "empty", "abstain_reasons": [], "z": None}
    evidence = receipt.get("evidence") or {}
    return {
        "state": receipt.get("state"),
        "abstain_reasons": [
            _reason_entry(token) for token in receipt.get("abstain_reasons") or []],
        "z": evidence.get("modified_z") if receipt.get("state") == "qualified" else None,
    }


def _clock_display(clocks: dict) -> dict:
    display = {}
    for name in ("observation", "source_publication", "ingestion", "computation"):
        clock = clocks.get(name)
        raw = clock.get("at") if isinstance(clock, dict) else None
        shown = format_clock(raw) if raw else None
        display[name] = {"at": raw,
                         "display": {"en": shown["en"], "zh": shown["zh"]} if shown else None}
    return display


def build_payload(*, universe, workspace, observations, fragility=None,
                  specimen=False) -> "dict | None":
    """Pure payload for the dislocation explorer; None when there is nothing
    honest to show (ruling R4: the tab then renders disabled)."""
    specimen = bool(specimen) and isinstance(fragility, dict)
    if not isinstance(observations, dict) or not isinstance(universe, dict):
        return None
    if not (universe.get("jurisdictions") or universe.get("aggregates")):
        return None
    bases = observations.get("bases")
    if not isinstance(bases, dict):
        return None
    usd_entries = [entry for entry in bases.get("usd_unhedged") or []
                   if isinstance(entry, dict)]
    local_entries = [entry for entry in bases.get("local") or []
                     if isinstance(entry, dict)]
    horizon = _horizon(workspace, usd_entries)
    if horizon is None:
        return None
    x_usd = sorted((entry for entry in usd_entries
                    if _identity(entry).get("horizon") == horizon),
                   key=lambda entry: (_identity(entry).get("universe_id") or "",
                                      entry.get("observation_id") or ""))
    x_local = [entry for entry in local_entries
               if _identity(entry).get("horizon") == horizon]
    if not x_usd:
        return None
    computed_at = _latest_computation(x_usd + x_local)
    if computed_at is None:
        return None
    local_by_market = {}
    for entry in x_local:
        local_by_market.setdefault(_identity(entry).get("universe_id"), entry)

    rows = []
    abstain_census = {}
    for subject in x_usd:
        identity = _identity(subject)
        market_id = identity.get("universe_id")
        region = region_of(market_id, universe)
        receipt = dislocation_peer_divergence(
            subject, x_usd, kind="peer_divergence_return",
            computed_at=computed_at, peer_rule="same_universe_region",
            universe=universe)
        evidence = receipt.get("evidence") or {}
        references = receipt.get("references") or {}
        excluded = references.get("excluded_by_reason") or {}

        extra_all = dislocation_peer_divergence(
            subject, x_usd, kind="peer_divergence_return",
            computed_at=computed_at, peer_rule="all_qualified", universe=universe)
        extra_fx = dislocation_peer_divergence(
            subject, x_usd, kind="peer_divergence_fx",
            computed_at=computed_at, peer_rule="same_universe_region",
            universe=universe)
        local_subject = local_by_market.get(market_id)
        extra_local = (dislocation_peer_divergence(
            local_subject, x_local, kind="peer_divergence_return",
            computed_at=computed_at, peer_rule="same_universe_region",
            universe=universe) if local_subject is not None else None)
        history = [entry for entry in x_usd
                   if _identity(entry).get("universe_id") == market_id
                   and entry.get("observation_id") != subject.get("observation_id")]
        extra_own = dislocation_own_history(
            subject, history, kind="own_history_return", computed_at=computed_at)

        observation_reasons = list(subject.get("abstain_reasons") or [])
        state, reasons = _view_state(observation_reasons, receipt)

        peers = {"region": region, "used": references.get("used"),
                 "offered": references.get("offered"), "items": []}
        if receipt.get("state") == "qualified":
            by_id = {entry.get("observation_id"): entry for entry in x_usd}
            items = []
            for observation_id in references.get("used_observation_ids") or []:
                peer = by_id.get(observation_id)
                if peer is None:
                    continue
                peer_market = _identity(peer).get("universe_id")
                peer_en, peer_zh = _market_names(universe, peer_market)
                decomposition = peer.get("decomposition") or {}
                peer_clock = format_clock(
                    ((peer.get("clocks") or {}).get("observation") or {}).get("at"))
                items.append({
                    "market_id": peer_market,
                    "name_en": peer_en, "name_zh": peer_zh,
                    "usd_pct": decomposition.get("usd_pct"),
                    "clock": ({"en": peer_clock["en"], "zh": peer_clock["zh"]}
                              if peer_clock else None),
                })
            items.sort(key=lambda item: item["market_id"] or "")
            peers["items"] = items[:5]

        for token in receipt.get("abstain_reasons") or []:
            abstain_census[token] = abstain_census.get(token, 0) + 1

        decomposition = subject.get("decomposition") or {}
        name_en, name_zh = _market_names(universe, market_id)
        rows.append({
            "market_id": market_id,
            "name_en": name_en,
            "name_zh": name_zh,
            "region": region,
            "dislocation_id": receipt.get("dislocation_id"),
            "state": receipt.get("state"),
            "abstain_reasons": list(receipt.get("abstain_reasons") or []),
            "z": evidence.get("modified_z"),
            "direction": evidence.get("direction"),
            "attention": evidence.get("attention"),
            "rank": evidence.get("rank"),
            "local_pct": decomposition.get("local_pct"),
            "fx_pct": decomposition.get("fx_pct"),
            "usd_pct": decomposition.get("usd_pct"),
            "interaction_pp": decomposition.get("interaction_pp"),
            "observation_state": subject.get("state"),
            "observation_reasons": list(observation_reasons),
            "clocks": receipt.get("clocks"),
            "clock_display": _clock_display(receipt.get("clocks") or {}),
            "references": {
                "used": references.get("used"),
                "offered": references.get("offered"),
                "used_observation_ids": references.get("used_observation_ids"),
                "excluded_by_reason": excluded,
            },
            "fragility": _fragility_of(fragility, market_id),
            "extras": {
                "all_qualified": _extra(extra_all),
                "local": _extra(extra_local),
                "fx": _extra(extra_fx),
                "own": _extra(extra_own),
            },
            "view_state": state,
            "view_reasons": reasons,
            "peers": peers,
            "index": None,
        })

    ranked, unranked = rank_rows(rows)
    overflow = max(0, sum(1 for row in rows if _rankable(row)) - RANK_CAP)
    rows = ranked + unranked

    scatter = _scatter_payload(rows)
    universe_markets_without_observation = len(
        (universe.get("jurisdictions") or {}).keys()
        - {_identity(entry).get("universe_id") for entry in x_usd})

    footnotes = []
    if not specimen:
        footnotes.append({"en": DISLOCATION_REASON_COPY["fragility_unadmitted"][0],
                          "zh": DISLOCATION_REASON_COPY["fragility_unadmitted"][1]})
    stance_en, stance_zh = reason_copy("stance_unadmitted")
    footnotes.append({"en": stance_en, "zh": stance_zh})
    if universe_markets_without_observation:
        coverage = COPY["footnote_coverage"]
        footnotes.append({
            "en": coverage[0].format(n=universe_markets_without_observation),
            "zh": coverage[1].format(n=universe_markets_without_observation)})
    if overflow:
        cap = COPY["footnote_cap"]
        footnotes.append({"en": cap[0].format(n=overflow), "zh": cap[1].format(n=overflow)})
    if observations.get("status") == "withheld":
        note = COPY["footnote_withheld"]
        footnotes.append({"en": note[0], "zh": note[1]})

    census = [{"token": token, "count": abstain_census[token],
               "text": {"en": _reason_pair(token)[0], "zh": _reason_pair(token)[1]}}
              for token in sorted(abstain_census)]
    computed_display = format_clock(computed_at)
    return {
        "horizon": horizon,
        "horizon_label": {"en": horizon_label(horizon)[0],
                          "zh": horizon_label(horizon)[1]},
        "basis": "usd_unhedged",
        "observation_status": observations.get("status"),
        "computed_at": computed_at,
        "computed_at_display": ({"en": computed_display["en"], "zh": computed_display["zh"]}
                                if computed_display else None),
        "specimen": specimen,
        "copy": {key: {"en": en, "zh": zh} for key, (en, zh) in COPY.items()},
        "rows": rows,
        "selected": 0 if ranked else None,
        "counts": {
            "carried": len(rows),
            "ranked": len(ranked),
            "unranked": len(unranked),
            "abstain_by_reason": abstain_census,
            "universe_markets_without_observation": universe_markets_without_observation,
        },
        "scatter": scatter,
        "thresholds": {"attention_modified_z": ATTENTION_MODIFIED_Z,
                       "fragility": FRAGILITY_THRESHOLD},
        "footnotes": footnotes,
        "census": census,
    }


def _scatter_payload(rows: list) -> dict:
    """Points for ranked rows with BOTH a finite fragility and a finite z;
    every other carried market lands in a Not-plotted chip (engine abstain
    reason first, else fragility_unadmitted)."""
    points, not_plotted = [], []
    for row in rows:
        market = row["market_id"]
        z = _finite(row.get("z"))
        fragility = _finite(row.get("fragility"))
        if row.get("index") is not None and z is not None and fragility is not None:
            clamped = abs(z) > _Z_SPAN
            drawn_z = max(-_Z_SPAN, min(_Z_SPAN, z))
            x = round(_SCATTER_X0 + fragility * _PX_PER_FRAGILITY, 1)
            y = round(_SCATTER_Y_MID - drawn_z * _PX_PER_Z, 1)
            points.append({
                "market_id": market, "x": x, "y": y,
                "fragility": fragility, "z": z,
                "direction": row.get("direction"),
                "clamped": clamped,
                "label_end": x > _SCATTER_X1 - 120.0,
            })
        elif row.get("abstain_reasons"):
            not_plotted.append({"market_id": market,
                                "reason": row["abstain_reasons"][0]})
        else:
            not_plotted.append({"market_id": market, "reason": "fragility_unadmitted"})
    for chip in not_plotted:
        chip["text"] = {"en": _reason_pair(chip["reason"])[0],
                        "zh": _reason_pair(chip["reason"])[1]}
    return {"points": points, "not_plotted": not_plotted,
            "empty": not points}


def build_view(*, universe, rights, contexts, workspace, observations=None) -> list:
    """Seam entry point (W2F contract): one dislocations panel, or [] when the
    payload is None (status 'empty', tab disabled). ``rights`` and
    ``contexts`` are accepted and unused — the IM15 receipt carries its own
    rights block and the binding context comes from the workspace config."""
    payload = None
    if observations is not None:
        payload = build_payload(universe=universe, workspace=workspace,
                                observations=observations)
    if payload is None:
        return []
    context = {"horizon": payload["horizon"]}
    config = (workspace or {}).get("config") or {}
    if "usd_unhedged" in (config.get("bases") or []):
        context["currency_basis"] = "usd_unhedged"
    return [{
        "view": "dislocations",
        "context_id": "im-gs-dislocations",
        "context": context,
        "payload": payload,
    }]
