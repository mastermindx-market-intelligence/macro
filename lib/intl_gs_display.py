"""Shared bilingual display vocabulary over the Wave 1 global universe.

INTL-GS-W2F-X (X1): one pure, no-I/O module both later view lanes read, so
IM13 (scanner/coverage) and IM14 (dossier) never duplicate or fork a label.
Imports only the frozen Wave 1 contracts (``engine.intl_global_universe``,
``engine.intl_global_observation``) and copies none of their constants: every
key set is derived against the imported tuples at test time. English names
always come from the universe ``name`` field; this module owns only the
Simplified Chinese renderings, the §10.6 region groups and the display copy.

An unknown token at runtime renders the raw token — it is never dropped and
never upgraded to a guessed class.
"""
from __future__ import annotations

import re

from engine.intl_global_observation import ABSTAIN_REASONS
from engine.intl_global_universe import CAPABILITIES, CAPABILITY_STATES

from datetime import date as _date, datetime as _datetime, timezone as _timezone

#: Simplified Chinese names for EXACTLY the 63 jurisdiction ids of
#: load_universe()["jurisdictions"] plus the "EZ" aggregate. The EN names are
#: the universe ``name`` field and are never copied here.
NAMES_ZH: dict[str, str] = {
    "AE": "阿联酋", "AR": "阿根廷", "AT": "奥地利", "AU": "澳大利亚",
    "BD": "孟加拉国", "BE": "比利时", "BH": "巴林", "BR": "巴西",
    "CA": "加拿大", "CH": "瑞士", "CL": "智利", "CN": "中国",
    "CO": "哥伦比亚", "CZ": "捷克", "DE": "德国", "DK": "丹麦",
    "EG": "埃及", "ES": "西班牙", "FI": "芬兰", "FR": "法国",
    "GB": "英国", "GR": "希腊", "HK": "香港", "HU": "匈牙利",
    "ID": "印度尼西亚", "IE": "爱尔兰", "IL": "以色列", "IN": "印度",
    "IR": "伊朗", "IS": "冰岛", "IT": "意大利", "JP": "日本",
    "KE": "肯尼亚", "KR": "韩国", "KW": "科威特", "KZ": "哈萨克斯坦",
    "LK": "斯里兰卡", "MA": "摩洛哥", "MX": "墨西哥", "MY": "马来西亚",
    "NG": "尼日利亚", "NL": "荷兰", "NO": "挪威", "NZ": "新西兰",
    "OM": "阿曼", "PE": "秘鲁", "PH": "菲律宾", "PK": "巴基斯坦",
    "PL": "波兰", "PT": "葡萄牙", "QA": "卡塔尔", "RO": "罗马尼亚",
    "RU": "俄罗斯", "SA": "沙特阿拉伯", "SE": "瑞典", "SG": "新加坡",
    "TH": "泰国", "TR": "土耳其", "TW": "台湾", "US": "美国",
    "VE": "委内瑞拉", "VN": "越南", "ZA": "南非",
    "EZ": "欧元区",
}

#: Spec R14 §10.6 region groups: (group key, universe regions, EN, ZH). Every
#: universe region appears in exactly one group and the groups sum to 63.
REGION_GROUPS = (
    ("asia", ("asia_pacific",), "Asia", "亚太"),
    ("emea", ("europe", "middle_east_africa"), "EMEA", "欧洲、中东及非洲"),
    ("americas", ("americas",), "Americas", "美洲"),
)

#: (EN, ZH) for EXACTLY the seven CAPABILITIES.
CAPABILITY_LABELS = {
    "equity_index_fx": ("Equity index + FX", "股指与汇率"),
    "constituent_breadth": ("Constituent breadth", "成分股广度"),
    "local_rates_credit": ("Local rates + credit", "本地利率与信用"),
    "dollar_funding_external": ("Dollar funding + external", "美元融资与外部"),
    "macro_policy": ("Macro + policy", "宏观与政策"),
    "us_exposure_transmission": ("US exposure + transmission", "美国敞口与传导"),
    "history_pit_rights": ("History + point-in-time rights", "历史与时点权利"),
}

#: PROPOSAL (orchestrator gap G4): universe CAPABILITY_STATES -> the §7 display
#: state keys ``_gs_macros.html.j2`` renders. ``delayed`` shows the Qualified
#: presentation with the delayed-source reason; ``unavailable`` and
#: ``not_applicable`` both render the Empty presentation with their own reason.
CAPABILITY_DISPLAY = {
    "qualified": "complete",
    "delayed": "qualified",
    "partial": "partial",
    "retained_stale": "stale",
    "market_closed": "closed",
    "suspended": "suspended",
    "unavailable": "empty",
    "denied": "restricted",
    "not_applicable": "empty",
}

#: (EN, ZH) short copy for the nine ABSTAIN_REASONS plus every capability
#: ``reason`` token the loaded universe carries. Tokens are data-derived at
#: test time; nothing here may shadow a contract reason.
REASON_COPY = {
    # --- engine.intl_global_observation.ABSTAIN_REASONS ---
    "clock_missing": ("Clock missing", "时钟缺失"),
    "clock_order_violation": ("Clock order violation", "时钟顺序违规"),
    "value_unavailable": ("Value unavailable", "数值不可用"),
    "return_identity_violation": ("Return identity violation", "回报恒等式违规"),
    "identity_mismatch": ("Identity mismatch", "标识不匹配"),
    "basis_unsupported": ("Hedged basis not supported", "不支持对冲口径"),
    "rights_unconfirmed": ("Rights unconfirmed", "权利未确认"),
    "incumbent_qualification_withheld": ("Incumbent qualification withheld", "现有资格认定未通过"),
    "source_evidence_missing": ("Source evidence missing", "缺少来源证据"),
    # --- capability reason tokens of the loaded universe ---
    "no_admitted_source": ("No admitted source", "无已准入数据源"),
    "no_rights_row": ("No rights row", "无权利记录"),
    "rights_unconfirmed_capability": ("Rights unconfirmed", "权利未确认"),
    "legacy_configured_eod_t_plus_2": ("Delayed end-of-day source", "延迟收盘数据源"),
    "fred_10y_only_no_curve_or_credit": ("10Y yield only; no curve or credit", "仅有10年期收益率；无曲线或信用"),
    "fred_oecd_subset": ("OECD macro subset", "OECD 宏观子集"),
    "history_retained_redistribution_scope_unresolved": (
        "History retained; redistribution scope unresolved", "历史保留；再分发范围未定"),
    # --- orchestrator display tokens (see VIEW_ABSTAIN_TOKENS) ---
    "evidence_tier_undefined": ("Evidence tier not yet defined", "证据层级尚未定义"),
    "common_factor_unadmitted": ("Common-factor model not admitted", "共同因子模型未准入"),
    "divergence_unadmitted": ("Divergence score not admitted", "背离评分未准入"),
    "series_unadmitted": ("Return history not admitted", "收益历史未准入"),
    "stance_unadmitted": ("No admitted stance source", "无已准入的立场来源"),
    "attention_unadmitted": ("No admitted attention ranking", "无已准入的关注排序"),
    "credit_funding_unadmitted": ("Credit and funding sources not admitted", "信用与融资数据源未准入"),
    "transmission_unadmitted": ("Transmission channels not admitted", "传导渠道未准入"),
    "us_corroboration_unadmitted": ("US corroboration not admitted", "美国佐证未准入"),
    "thesis_unadmitted": ("No admitted thesis", "无已准入的论点"),
    "session_calendar_unadmitted": ("Session calendar not admitted", "交易时段日历未准入"),
    "corrections_none": ("No corrections recorded", "暂无更正记录"),
}

#: The view-abstain display tokens shared by the IM13 and IM14 view lanes, in
#: order. None of them is an ABSTAIN_REASONS member or a data-derived
#: capability reason token, so no contract reason is ever shadowed.
VIEW_ABSTAIN_TOKENS = (
    "common_factor_unadmitted",
    "divergence_unadmitted",
    "series_unadmitted",
    "stance_unadmitted",
    "attention_unadmitted",
    "credit_funding_unadmitted",
    "transmission_unadmitted",
    "us_corroboration_unadmitted",
    "thesis_unadmitted",
    "session_calendar_unadmitted",
    "corrections_none",
)

#: Spec R14 §10.6 coverage columns. PROPOSAL (orchestrator gap G5): the
#: field -> capability binding; constituent_breadth, macro_policy and
#: history_pit_rights carry no §10.6 column.
COVERAGE_FIELDS = (
    ("index_close", "INDEX CLOSE", "指数收盘", "equity_index_fx"),
    ("fx_fix", "FX FIX", "汇率定盘", "equity_index_fx"),
    ("y10", "10Y YIELD", "10年期收益率", "local_rates_credit"),
    ("cds5y", "CDS 5Y", "5年期CDS", "local_rates_credit"),
    ("usd_funding", "USD FUNDING", "美元融资", "dollar_funding_external"),
    ("us_proxy", "US PROXY", "美国代理", "us_exposure_transmission"),
)

#: (EN, ZH) for the rights classes present in load_rights_matrix()["rows"].
#: An unknown class renders the raw token — never dropped, never upgraded.
RIGHTS_CLASS_LABELS = {
    "direct_display_ok": ("Display permitted", "允许展示"),
    "internal_only": ("Internal only", "仅限内部"),
    "unresolved": ("Rights unresolved", "权利待定"),
}

#: The R14 spec names T1/T2/T3 evidence tiers but neither the spec nor any
#: Wave 1 contract defines what produces a tier. No mapping is invented here.
EVIDENCE_TIER_SOURCE = None  # open seat gap: evidence-tier definition (IM13/IM14 seat ruling)

_REGION_GROUP_OF = {
    region: group for group, regions, _en, _zh in REGION_GROUPS for region in regions}


def _display_state(entry: dict) -> str:
    return CAPABILITY_DISPLAY.get(entry.get("state"), entry.get("state"))


def jurisdiction_rows(universe: dict) -> list[dict]:
    """One display row per jurisdiction (universe order) then per aggregate.

    ``capabilities`` keeps the universe's verbatim state/reason/evidence and
    adds the ``display`` key (the §7 presentation state). Pure: reads only the
    passed document.
    """
    rows: list[dict] = []
    for jid, jur in (universe.get("jurisdictions") or {}).items():
        rows.append({
            "id": jid,
            "kind": "jurisdiction",
            "name_en": jur.get("name"),
            "name_zh": NAMES_ZH.get(jid, jid),
            "region": jur.get("region"),
            "region_group": _REGION_GROUP_OF.get(jur.get("region")),
            "cohort": jur.get("cohort"),
            "currency": jur.get("currency"),
            "timezone": jur.get("timezone"),
            "capabilities": {
                capability: {
                    "state": entry.get("state"),
                    "display": _display_state(entry),
                    "reason": entry.get("reason"),
                }
                for capability, entry in (jur.get("capabilities") or {}).items()
            },
        })
    for aid, agg in (universe.get("aggregates") or {}).items():
        rows.append({
            "id": aid,
            "kind": "aggregate",
            "name_en": agg.get("name"),
            "name_zh": NAMES_ZH.get(aid, aid),
            "region": None,
            "region_group": None,
            "cohort": None,
            "currency": agg.get("currency"),
            "timezone": None,
            "capabilities": {
                capability: {
                    "state": entry.get("state"),
                    "display": _display_state(entry),
                    "reason": entry.get("reason"),
                }
                for capability, entry in (agg.get("capabilities") or {}).items()
            },
        })
    return rows


def rights_view(universe: dict, rights_matrix: dict, jurisdiction_id: str,
                capability: str) -> dict | None:
    """Project the rights row behind one jurisdiction/capability pair.

    Returns None when the capability's ``rights_ref`` is null. A rights_ref
    naming no matrix row returns ``rights_class`` None with the
    "Rights row missing" copy — never a guessed class. Reads only the two
    passed documents.
    """
    source = None
    jurisdictions = universe.get("jurisdictions") or {}
    aggregates = universe.get("aggregates") or {}
    holder = jurisdictions.get(jurisdiction_id) or aggregates.get(jurisdiction_id)
    if holder is not None:
        source = (holder.get("capabilities") or {}).get(capability)
    if source is None:
        return None
    ref = source.get("rights_ref")
    if ref is None:
        return None
    row = next((entry for entry in (rights_matrix.get("rows") or [])
                if isinstance(entry, dict) and entry.get("id") == ref), None)
    if row is None:
        return {
            "rights_ref": ref,
            "rights_class": None,
            "label_en": "Rights row missing",
            "label_zh": "权利记录缺失",
            "delay": None,
            "decision_ref": None,
            "review_status": None,
        }
    rights_class = row.get("rights_class")
    label_en, label_zh = RIGHTS_CLASS_LABELS.get(rights_class, (rights_class, rights_class))
    review = row.get("review") if isinstance(row.get("review"), dict) else {}
    return {
        "rights_ref": ref,
        "rights_class": rights_class,
        "label_en": label_en,
        "label_zh": label_zh,
        "delay": row.get("delay"),
        "decision_ref": row.get("decision_ref"),
        "review_status": (review or {}).get("status"),
    }


def reason_copy(token: str) -> tuple[str, str]:
    """(EN, ZH) for a token; an unknown token renders the raw token twice."""
    return REASON_COPY.get(token, (token, token))


#: Three-letter English month abbreviations (spec §13.3 Dates row).
_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def format_clock(value):
    """One clock instant -> the §13.3 display vocabulary (FX1).

    Accepts an ISO-8601 date or datetime string, or a date/datetime object.
    A datetime converts to UTC first ("Z", "+00:00" and naive = already UTC;
    "2026-10-09T23:30:00+08:00" -> 15:30 UTC) and returns
    ``{"datetime": <original ISO string>, "en": "9 Oct 15:00 UTC",
    "zh": "10月9日 15:00 UTC"}`` (day without leading zero, three-letter
    English month, 24h HH:MM, literal "UTC"). A date-only value returns the
    date form ``{"datetime": "2026-10-07", "en": "7 Oct 2026",
    "zh": "2026年10月7日"}`` — the spec has no date-only format, so this is the
    PROPOSAL recorded under Gaps for a seat ruling. None or "" returns None;
    an unparseable value raises ValueError — it is never echoed into markup.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("clock value is not a date or datetime")
    if isinstance(value, _datetime):
        moment = value if value.tzinfo is None else value.astimezone(_timezone.utc)
        return {"datetime": value.isoformat(),
                "en": "%d %s %02d:%02d UTC" % (moment.day, _MONTHS_EN[moment.month - 1],
                                               moment.hour, moment.minute),
                "zh": "%d月%d日 %02d:%02d UTC" % (moment.month, moment.day,
                                                  moment.hour, moment.minute)}
    if isinstance(value, _date):
        return {"datetime": value.isoformat(),
                "en": "%d %s %d" % (value.day, _MONTHS_EN[value.month - 1], value.year),
                "zh": "%d年%d月%d日" % (value.year, value.month, value.day)}
    if not isinstance(value, str):
        raise ValueError("clock value is not a date or datetime")
    text = value
    if _DATE_ONLY.match(text):
        parsed = _date.fromisoformat(text)
        return {"datetime": text,
                "en": "%d %s %d" % (parsed.day, _MONTHS_EN[parsed.month - 1], parsed.year),
                "zh": "%d年%d月%d日" % (parsed.year, parsed.month, parsed.day)}
    try:
        parsed = _datetime.fromisoformat(text.replace("Z", "+00:00", 1)
                                         if text.endswith("Z") else text)
    except ValueError:
        raise ValueError("clock value is not an ISO-8601 date or datetime") from None
    moment = parsed if parsed.tzinfo is None else parsed.astimezone(_timezone.utc)
    return {"datetime": text,
            "en": "%d %s %02d:%02d UTC" % (moment.day, _MONTHS_EN[moment.month - 1],
                                           moment.hour, moment.minute),
            "zh": "%d月%d日 %02d:%02d UTC" % (moment.month, moment.day,
                                              moment.hour, moment.minute)}


def snapshot_display(snapshot):
    """Add the FX1 clock display to one mount snapshot block (per basis).

    ``snapshot`` is the ``_snapshot_clocks`` shape ``{basis: {clocks, …}}``.
    Returns one dict per basis with the existing raw ``clocks`` UNCHANGED
    (machine contract) plus ``clock_display`` mapping every clock key to
    ``format_clock(raw)`` or None. The single composition path for the mount,
    the fixture site and the snapshot macro — no caller formats a clock itself.
    """
    displayed = {}
    for basis, entry in (snapshot or {}).items():
        clocks = (entry or {}).get("clocks") or {}
        displayed[basis] = dict(entry or {}, clock_display={
            clock: (format_clock(raw) if raw else None) for clock, raw in clocks.items()})
    return displayed


#: FX5 horizon vocabulary. EN uppercase follows the spec's "USD 20D"; the ZH
#: forms follow the estate convention (templates/heatmap.js,
#: templates/market_structure.html.j2). The spec carries no ZH horizon copy —
#: recorded under Gaps as a PROPOSAL for a seat ruling. Unknown ids pass
#: through verbatim (never dropped, never upgraded).
_HORIZON_LABELS = {"1m": ("1M", "1月"), "3m": ("3M", "3月"), "20d": ("20D", "20日")}


def horizon_label(horizon):
    """(EN, ZH) for one horizon id; any other id renders the raw id twice."""
    return _HORIZON_LABELS.get(horizon, (horizon, horizon))


assert set(CAPABILITY_LABELS) == set(CAPABILITIES)
assert set(CAPABILITY_DISPLAY) == set(CAPABILITY_STATES)
assert not (set(VIEW_ABSTAIN_TOKENS) & set(ABSTAIN_REASONS))
