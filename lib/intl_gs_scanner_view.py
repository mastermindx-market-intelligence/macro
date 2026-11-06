"""IM13 global scanner view builder (INTL-GS Wave 2, packet INTL-GS-W2A).

One panel per mount context ``(horizon, currency_basis)`` the workspace
declares for the local and usd_unhedged bases — hedged is never a context.
Every market number is a QUALIFIED Wave 1 observation value or decomposition
field handed in through ``attach_surveillance(observations=...)``; nothing is
computed here. Every element without an admitted source renders its §7 state
with the foundation's REASON_COPY token (L10). Coverage is counts and
capability states, never a percentage. Specimen values never enter this
module: ``specimen`` cannot be set on any code path (test-isolated).
"""
from __future__ import annotations

from engine.intl_global_observation import CURRENCY_BASES  # noqa: F401  (contract import)
from lib.intl_gs_display import (
    CAPABILITY_DISPLAY,
    REASON_COPY,
    RIGHTS_CLASS_LABELS,
    format_clock,
    horizon_label,
    jurisdiction_rows,
    rights_view,
)

# View-owned display copy (EN, ZH). Board-literal where the R14 scanner board
# carries the string; every other phrase is §7 state copy via REASON_COPY.
EYEBROW = ("Global surveillance · Scanner", "全球监测 · 扫描")
TITLE = ("Global scanner", "全球扫描")
LEDE = ("What moved overnight, why it moved, and whether it reaches US assets.",
        "隔夜什么在动、为何而动，以及是否会传导至美国资产。")
KPI_BREADTH = ("Breadth · Up in USD", "广度 · 美元口径上涨")
KPI_LARGEST = ("Largest USD move", "最大美元口径变动")
KPI_COMMON = ("EM FX common factor", "新兴市场汇率共同因子")
KPI_SPREAD = ("EM sovereign spread", "新兴市场主权利差")
BREADTH_MARKETS = ("markets", "个市场")
HANDOFF_SESSIONS = (
    ("Asia close", "亚洲收盘"),
    ("Europe open", "欧洲开盘"),
    ("US pre-market", "美股盘前"),
)
SESSION_TOKEN = "session_calendar_unadmitted"
COMMON_TOKEN = "common_factor_unadmitted"
DIVERGENCE_TOKEN = "divergence_unadmitted"
SERIES_TOKEN = "series_unadmitted"
STANCE_TOKEN = "stance_unadmitted"
ATTENTION_TOKEN = "attention_unadmitted"
BAND_TOKENS = (
    (3, "credit_funding_unadmitted"),
    (4, "transmission_unadmitted"),
    (5, "us_corroboration_unadmitted"),
    (6, "thesis_unadmitted"),
)
DELAY_T_PLUS_2 = ("Delayed end-of-day source · T+2", "延迟收盘数据源 · T+2")
NO_RIGHTS_ROW = ("No rights row", "无权利记录")
DASH = "—"


def _pair(token):
    return REASON_COPY.get(token, (token, token))


def _observation_index(observations, basis, horizon):
    """{market_id: observation} for one basis+horizon; {} when withheld."""
    if not observations:
        return {}
    entries = (observations.get("bases") or {}).get(basis) or []
    return {entry["identity"]["market_id"]: entry for entry in entries
            if isinstance(entry, dict)
            and entry["identity"].get("horizon") == horizon}


def _leg(observation):
    """One numeric leg: qualified value or the honest abstain with reasons."""
    if observation is None:
        return {"state": "abstain", "pct": None, "reasons": [], "first_reason": None,
                "copies": []}
    if observation.get("state") == "qualified":
        return {"state": "qualified", "pct": observation["value"]["pct"],
                "reasons": [], "first_reason": None}
    reasons = list(observation.get("abstain_reasons") or [])
    return {"state": "abstain", "pct": None, "reasons": reasons,
            "first_reason": _pair(reasons[0]) if reasons else None,
            "copies": [_pair(reason) for reason in reasons]}


def _fx_leg(usd_observation):
    """FX % reads the usd observation's decomposition, never a local calc."""
    if usd_observation is not None and usd_observation.get("state") == "qualified":
        decomposition = usd_observation.get("decomposition") or {}
        return {"state": "qualified", "pct": decomposition.get("fx_pct"),
                "reasons": [], "first_reason": None,
                "local_pct": decomposition.get("local_pct"),
                "additive_fx_contribution_pp": decomposition.get("additive_fx_contribution_pp"),
                "interaction_pp": decomposition.get("interaction_pp")}
    leg = _leg(usd_observation)
    leg.update({"local_pct": None, "additive_fx_contribution_pp": None,
                "interaction_pp": None})
    return leg


def _delay_copy(delay):
    delay = delay or ""
    return DELAY_T_PLUS_2 if "tplus2" in delay else None


def _tier_data(universe_row, universe, rights, jid):
    """TIER slot data: the rights label from the foundation's own rights_view,
    or the empty grammar when rights_ref is null - never a guessed class."""
    capability = (universe_row.get("capabilities") or {}).get("equity_index_fx") or {}
    data = {
        "capability_display": capability.get("display"),
        "capability_reason": _pair(capability["reason"]) if capability.get("reason") else None,
        "delay": None,
        "rights_class": None,
        "label": NO_RIGHTS_ROW,
    }
    view = rights_view(universe, rights, jid, "equity_index_fx")
    if view is not None:
        data["rights_class"] = view["rights_class"]
        data["label"] = (view["label_en"], view["label_zh"])
        data["delay"] = _delay_copy(view["delay"])
    return data


def _market_rows(universe, rights, horizon, observations, linkable):
    local_index = _observation_index(observations, "local", horizon)
    usd_index = _observation_index(observations, "usd_unhedged", horizon)
    rows, nodata = [], []
    for entry in jurisdiction_rows(universe):
        local_obs = local_index.get(entry["id"])
        usd_obs = usd_index.get(entry["id"])
        if local_obs is None and usd_obs is None:
            capability = (entry["capabilities"] or {}).get("equity_index_fx") or {}
            nodata.append({
                "id": entry["id"], "name_en": entry["name_en"], "name_zh": entry["name_zh"],
                "state_display": capability.get("display"),
                "reason": _pair(capability.get("reason")) if capability.get("reason") else None,
                "reason_token": capability.get("reason"),
            })
            continue
        clock_source = usd_obs if usd_obs is not None and usd_obs.get("state") == "qualified" \
            else (local_obs if local_obs is not None and local_obs.get("state") == "qualified"
                  else None)
        market_sub = None
        if clock_source is not None:
            market_sub = {
                "index_id": clock_source["identity"].get("index_id"),
                "currency": entry.get("currency"),
                "clock": format_clock(clock_source["clocks"]["observation"]["at"]),
            }
        rows.append({
            "id": entry["id"], "name_en": entry["name_en"], "name_zh": entry["name_zh"],
            "kind": entry["kind"], "linkable": entry["id"] in linkable,
            "local": _leg(local_obs),
            "usd": _leg(usd_obs),
            "fx": _fx_leg(usd_obs),
            "market_sub": market_sub,
            "tier": _tier_data(entry, universe, rights, entry["id"]),
        })
    qualified = [row for row in rows if row["usd"]["state"] == "qualified"]
    abstaining = [row for row in rows if row["usd"]["state"] != "qualified"]
    qualified.sort(key=lambda row: -row["usd"]["pct"])
    abstaining.sort(key=lambda row: row["name_en"])
    return qualified + abstaining, nodata


def _kpi_cards(horizon, usd_index, universe_rows, universe, rights):
    qualified = [obs for obs in usd_index.values()
                 if isinstance(obs, dict) and obs.get("state") == "qualified"]
    tier_abstain = {"tier_abstain": True, "label": _pair("evidence_tier_undefined")}
    cards = []
    if qualified:
        latest_clock = max(obs["clocks"]["computation"]["at"] for obs in qualified)
        cards.append({"id": "breadth", "kind": "breadth",
                      "up": sum(1 for obs in qualified if obs["value"]["pct"] > 0),
                      "qualified": len(qualified),
                      "clock": format_clock(latest_clock),
                      "tier": tier_abstain})
    else:
        cards.append({"id": "breadth", "kind": "abstain", "token": "value_unavailable",
                      "reason": _pair("value_unavailable"), "tier": tier_abstain})
    if qualified:
        largest = max(qualified, key=lambda obs: abs(obs["value"]["pct"]))
        holder = next(row for row in universe_rows
                      if row["id"] == largest["identity"]["market_id"])
        name_zh = holder["name_zh"]
        decomposition = largest.get("decomposition") or {}
        cards.append({"id": "largest", "kind": "move", "pct": largest["value"]["pct"],
                      "ink": "up" if largest["value"]["pct"] > 0 else
                             ("down" if largest["value"]["pct"] < 0 else ""),
                      "market": (f"{largest['identity']['market_id']} "
                                 f"{largest['identity'].get('index_id') or ''}".strip(),
                                 name_zh),
                      "local_pct": decomposition.get("local_pct"),
                      "fx_pct": decomposition.get("fx_pct"),
                      "clock": format_clock(largest["clocks"]["observation"]["at"]),
                      "tier": _tier_data(holder, universe, rights, holder["id"])})
    else:
        cards.append({"id": "largest", "kind": "abstain", "token": "value_unavailable",
                      "reason": _pair("value_unavailable"), "tier": tier_abstain})
    cards.append({"id": "common_factor", "kind": "abstain", "token": COMMON_TOKEN,
                  "reason": _pair(COMMON_TOKEN), "tier": tier_abstain})
    cards.append({"id": "spread", "kind": "abstain", "token": "credit_funding_unadmitted",
                  "reason": _pair("credit_funding_unadmitted"), "tier": tier_abstain})
    return cards


def build_view(*, universe, rights, contexts, workspace, observations=None):
    panels = []
    config = (workspace or {}).get("config") or {}
    linkable = set(config.get("markets") or ())
    universe_rows = jurisdiction_rows(universe)
    for _context_id, context in (contexts or {}).items():
        horizon = context["horizon"]
        basis = context["currency_basis"]
        if basis not in ("local", "usd_unhedged"):
            continue
        rows, nodata = _market_rows(universe, rights, horizon, observations, linkable)
        usd_index = _observation_index(observations, "usd_unhedged", horizon)
        # KPI tier chips need the universe rows for rights lookups; keep the
        # real rights document on the largest card through the tier helper.
        cards = _kpi_cards(horizon, usd_index, universe_rows, universe, rights)
        qualified_rows = sum(1 for row in rows if row["usd"]["state"] == "qualified")
        horizon_pair = horizon_label(horizon)
        market_scope = []
        for row in universe_rows:
            if row["id"] in linkable:
                capability = (row["capabilities"] or {}).get("equity_index_fx") or {}
                tier = _tier_data(row, universe, rights, row["id"])
                market_scope.append({"id": row["id"], "name": (row["name_en"], row["name_zh"]),
                                     "tier": tier,
                                     "capability_display": capability.get("display"),
                                     "capability_reason":
                                         _pair(capability.get("reason"))
                                         if capability.get("reason") else None})
        payload = {
            "specimen": False,
            "horizon": {"id": horizon, "en": horizon_pair[0], "zh": horizon_pair[1]},
            "basis": {"id": basis},
            "header": {"eyebrow": EYEBROW, "title": TITLE, "lede": LEDE},
            "kpi": cards,
            "handoff": [{"name": pair} for pair in HANDOFF_SESSIONS],
            "session_copy": _pair(SESSION_TOKEN),
            "abstain": {
                "common": {"token": COMMON_TOKEN, "reason": _pair(COMMON_TOKEN)},
                "divergence": {"token": DIVERGENCE_TOKEN, "reason": _pair(DIVERGENCE_TOKEN)},
                "series": {"token": SERIES_TOKEN, "reason": _pair(SERIES_TOKEN)},
                "stance": {"token": STANCE_TOKEN, "reason": _pair(STANCE_TOKEN)},
                "attention": {"token": ATTENTION_TOKEN, "reason": _pair(ATTENTION_TOKEN)},
                "session": {"token": SESSION_TOKEN, "reason": _pair(SESSION_TOKEN)},
                "bands": [{"q": q, "token": token, "reason": _pair(token)}
                          for q, token in BAND_TOKENS],
            },
            "rows": rows,
            "nodata": {"count": len(nodata), "markets": nodata},
            "counts": {"rows": len(rows), "qualified": qualified_rows,
                       "abstain": len(rows) - qualified_rows, "nodata": len(nodata)},
            "market_scope": market_scope,
            "footnote": {
                "source": (observations or {}).get("source_reference"),
                "withheld_copy": _pair("source_evidence_missing"),
                "delay": DELAY_T_PLUS_2,
            },
        }
        panels.append(dict(view="scanner",
                           context_id=f"im-gs-scanner-{horizon}-{basis}",
                           context={"horizon": horizon, "currency_basis": basis},
                           generation=None, payload=payload))
    return panels
