"""IM14 market dossier (INTL-GS-W2B): the per-jurisdiction dossier view.

Spec R14 §10.5 (board 11) over the Wave 1 observation contract. One panel per
binding context (horizon, currency_basis) the mount passes, never usd_hedged
(the snapshot bar shows hedged as its Abstain segment). Every number on the
page is the value, decomposition or clock of a QUALIFIED observation handed in
through ``observations`` — this module computes no z-score, factor, stance,
rank, sparkline or percentage of its own (L10). Everything without an admitted
source renders its §7 state with the foundation's REASON_COPY.

The IM16 seat binding for the Q2·Q3 credit/funding table reads
``engine.intl_global_acceptance_matrix.acceptance_matrix`` (coverage-board
cells for the 10Y/CDS/USD-funding rows) and
``engine.intl_global_dollar_credit.jurisdiction_assessments`` (EM credit ·
sovereign, Dollar funding): pure engine outputs, imported and never copied.

No specimen path exists here: ``build_view`` can never set the specimen flag;
only the test fixture renders specimen payloads (tests/test_intl_gs_dossier.py
proves it).
"""
from __future__ import annotations

from engine.intl_global_acceptance_matrix import acceptance_matrix
from engine.intl_global_dollar_credit import (
    ABSTAIN_REASONS as _DOLLAR_ABSTAIN_REASONS, jurisdiction_assessments)
from engine.intl_global_observation import REQUIRED_CLOCKS
from engine.intl_global_universe import CAPABILITIES
from lib.intl_gs_display import (
    CAPABILITY_DISPLAY, CAPABILITY_LABELS, COVERAGE_FIELDS, EVIDENCE_TIER_SOURCE,
    REASON_COPY, REGION_GROUPS, VIEW_ABSTAIN_TOKENS, format_clock, horizon_label,
    jurisdiction_rows, reason_copy, rights_view, snapshot_display)
from lib.intl_surveillance_mount import _snapshot_clocks

#: IM16 REASON SUPPLEMENT (seat directive): EN+ZH copy for the members of
#: engine.intl_global_dollar_credit.ABSTAIN_REASONS the foundation REASON_COPY
#: lacks — keyed ONLY by ABSTAIN_REASONS members, never shadowing a contract
#: reason. Recorded as a GAP for foldback into lib/intl_gs_display.py.
IM16_REASON_COPY = {
    "insufficient_history": ("Insufficient history", "历史数据不足"),
    "stale_input": ("Stale input", "输入过期"),
    "proxy_population_mismatch": ("Proxy population mismatch", "代理样本不匹配"),
    "funding_observation_unavailable": ("Funding observation unavailable",
                                        "融资观测不可用"),
    "capability_not_qualified": ("Capability not qualified", "能力未达标"),
}

#: Display copy (not contract constants) for the two assessment claim rows.
_EM_CREDIT_LABEL = ("EM credit · sovereign", "EM 信用 · 主权")
_DOLLAR_FUNDING_LABEL = ("Dollar funding", "美元融资")

#: The §5 clock labels, matching the foundation snapshot macro vocabulary.
_CLOCK_LABELS = (
    ("observation", "Reference period", "参考区间"),
    ("source_publication", "Source available", "来源可得"),
    ("ingestion", "Acquired + qualified", "采集并合格"),
    ("computation", "Published", "发布"),
)

_CLOCK_PRECISION_WORDS = {
    "exact": ("exact", "精确"),
    "upper_bound": ("upper bound", "上界"),
    "session_date": ("session date", "交易日"),
}

#: R14 §10.6 label vocabulary (foundation COVERAGE_FIELDS) keyed by the IM16
#: coverage-board column the dossier credit/funding table reads.
_BOARD_ROW_LABELS = {}
for _field_id, _en, _zh, _capability in COVERAGE_FIELDS:
    _column = {"y10": "yield_10y", "cds5y": "cds_5y"}.get(_field_id, _field_id)
    if _column in ("yield_10y", "cds_5y", "usd_funding"):
        _BOARD_ROW_LABELS[_column] = (_en, _zh)

assert set(_BOARD_ROW_LABELS) == {"yield_10y", "cds_5y", "usd_funding"}
assert set(IM16_REASON_COPY) <= set(_DOLLAR_ABSTAIN_REASONS)
assert tuple(key for key, _en, _zh in _CLOCK_LABELS) == REQUIRED_CLOCKS


def _im16_reason_copy(token):
    """(EN, ZH) preferring the foundation copy, then the IM16 supplement."""
    if token in REASON_COPY:
        return reason_copy(token)
    return IM16_REASON_COPY.get(token, (token, token))


def _signed_text(value, dp=2, unit=""):
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{abs(value):.{dp}f}{unit}"


def _residual_text(residual):
    if 0 < abs(residual) < 1e-6:
        return f"{residual:.1e}".replace("-", "−")
    return _signed_text(residual, 2, "pp")


def _reason_pairs(tokens):
    return [reason_copy(token) for token in (tokens or [])]


def _observation_index(observations):
    """(market_id, horizon, basis) -> observation, over the passed set."""
    index = {}
    for basis, entries in ((observations or {}).get("bases") or {}).items():
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            identity = entry.get("identity") or {}
            index[(identity.get("market_id"), identity.get("horizon"), basis)] = entry
    return index


def _capability_reason_pair(row, capability):
    entry = (row["capabilities"] or {}).get(capability) or {}
    return reason_copy(entry.get("reason")) if entry.get("reason") else (
        "No admitted source", "无已准入数据源")


def _hero(row, observation):
    capability_pair = _capability_reason_pair(row, "equity_index_fx")
    if observation is not None and observation.get("state") == "qualified":
        value = (observation.get("value") or {}).get("pct")
        clock = format_clock(((observation.get("clocks") or {}).get("observation")
                              or {}).get("at"))
        if value is not None and clock is not None:
            return {"state": "qualified", "qualified": True, "value_pct": value,
                    "clock": clock, "reason_pairs": None, "reason_tokens": []}
    if observation is not None:
        reasons = observation.get("abstain_reasons") or []
        return {"state": "abstain", "qualified": False, "value_pct": None,
                "clock": None, "reason_pairs": _reason_pairs(reasons) or [capability_pair],
                "reason_tokens": list(reasons)}
    return {"state": "no_observation", "qualified": False, "value_pct": None,
            "clock": None, "reason_pairs": [capability_pair], "reason_tokens": []}


def _decomposition(row, usd_observation):
    capability_pair = _capability_reason_pair(row, "equity_index_fx")
    decomposition = (usd_observation or {}).get("decomposition") \
        if (usd_observation or {}).get("state") == "qualified" else None
    if not isinstance(decomposition, dict):
        reasons = (usd_observation or {}).get("abstain_reasons")
        pairs = _reason_pairs(reasons) if reasons else [capability_pair]
        return {"available": False, "reason_pairs": pairs}
    local = decomposition["local_pct"]
    additive = decomposition["additive_fx_contribution_pp"]
    interaction = decomposition["interaction_pp"]
    usd = decomposition["usd_pct"]
    residual = decomposition["identity_residual"]
    residual_text = _residual_text(residual)
    identity_en = (
        "Identity check: local " + _signed_text(local, 2, "%")
        + " + FX " + _signed_text(decomposition["fx_pct"], 2, "%")
        + " + interaction " + _signed_text(interaction, 2, "pp")
        + " = USD " + _signed_text(usd, 2, "%")
        + " (residual " + residual_text + ").")
    identity_zh = (
        "恒等式：本币 " + _signed_text(local, 2, "%")
        + " + 汇率 " + _signed_text(decomposition["fx_pct"], 2, "%")
        + " + 交互项 " + _signed_text(interaction, 2, "pp")
        + " = 美元 " + _signed_text(usd, 2, "%")
        + " （残差 " + residual_text + "）。")
    payload = {"available": True, "reason_pairs": None,
               "identity_en": identity_en, "identity_zh": identity_zh,
               "identity_residual_text": residual_text}
    payload.update({key: decomposition[key] for key in decomposition})
    return payload


def _clocks(observation):
    clocks = (observation or {}).get("clocks") or {}
    rows = []
    for key, en, zh in _CLOCK_LABELS:
        entry = clocks.get(key) or {}
        at = entry.get("at") if isinstance(entry, dict) else None
        precision = entry.get("precision") if isinstance(entry, dict) else None
        display = format_clock(at) if at else None
        precision_pair = _CLOCK_PRECISION_WORDS.get(precision)
        rows.append({
            "key": key, "label_en": en, "label_zh": zh,
            "display": display,
            "precision_en": precision_pair[0] if precision_pair else None,
            "precision_zh": precision_pair[1] if precision_pair else None,
            "missing": display is None,
        })
    return rows


def _credit_funding(row, board_cells, assessments):
    """The five IM16-binding rows, in order, states verbatim from the engine."""
    rows = []
    for column_id in ("yield_10y", "cds_5y", "usd_funding"):
        cell = (board_cells or {}).get(row["id"], {}).get(column_id)
        if cell is None:
            # The aggregate carries no IM16 board cell: the IM11 capability
            # state of the column's capability is the honest fallback (GAP).
            capability = {"yield_10y": "local_rates_credit",
                          "cds_5y": "local_rates_credit",
                          "usd_funding": "dollar_funding_external"}[column_id]
            entry = (row["capabilities"] or {}).get(capability) or {}
            cell = {"state": entry.get("state") or "unavailable",
                    "reason": entry.get("reason") or "no_admitted_source"}
        label_en, label_zh = _BOARD_ROW_LABELS[column_id]
        rows.append({"id": column_id, "label_en": label_en, "label_zh": label_zh,
                     "state": cell.get("state"),
                     "display": CAPABILITY_DISPLAY.get(cell.get("state"),
                                                       cell.get("state")),
                     "reason": cell.get("reason"),
                     "reason_en": reason_copy(cell.get("reason"))[0],
                     "reason_zh": reason_copy(cell.get("reason"))[1],
                     "all_reasons": [cell.get("reason")]})
    for claim, label in (("em_credit_sovereign", _EM_CREDIT_LABEL),
                         ("dollar_funding", _DOLLAR_FUNDING_LABEL)):
        assessment = ((assessments or {}).get(claim, {})
                      .get("jurisdictions", {}).get(row["id"]))
        if assessment is None:
            reasons = ["capability_not_qualified"]
        else:
            reasons = assessment.get("abstain_reasons") or ["capability_not_qualified"]
        first_en, first_zh = _im16_reason_copy(reasons[0])
        rows.append({"id": claim, "label_en": label[0], "label_zh": label[1],
                     "state": (assessment or {}).get("state") or "abstain",
                     "display": "abstain",
                     "reason": reasons[0],
                     "reason_en": first_en, "reason_zh": first_zh,
                     "all_reasons": list(reasons)})
    return rows


def _external_vulnerability(row, board_cells):
    cell = (board_cells or {}).get(row["id"], {}).get("dollar_funding_external")
    if cell is None:
        entry = (row["capabilities"] or {}).get("dollar_funding_external") or {}
        cell = {"state": entry.get("state") or "unavailable",
                "reason": entry.get("reason") or "no_admitted_source"}
    return {"state": cell.get("state"), "reason": cell.get("reason"),
            "reason_en": reason_copy(cell.get("reason"))[0],
            "reason_zh": reason_copy(cell.get("reason"))[1],
            "display": CAPABILITY_DISPLAY.get(cell.get("state"), cell.get("state"))}


def _coverage_vector(row):
    vector = []
    for capability in CAPABILITIES:
        entry = (row["capabilities"] or {}).get(capability) or {}
        reason = entry.get("reason")
        pair = reason_copy(reason) if reason else ("No admitted source", "无已准入数据源")
        label_en, label_zh = CAPABILITY_LABELS[capability]
        vector.append({"capability": capability, "label_en": label_en,
                       "label_zh": label_zh, "display": entry.get("display"),
                       "reason_en": pair[0], "reason_zh": pair[1]})
    return vector


def _peers(row, rows_by_id, order, horizon, basis, index):
    group = row["region_group"]
    peers = []
    if not group:
        return peers
    for peer_id in order:
        if len(peers) == 5:
            break
        if peer_id == row["id"]:
            continue
        peer = rows_by_id[peer_id]
        if peer["region_group"] != group or peer["kind"] != "jurisdiction":
            continue
        observation = index.get((peer_id, horizon, basis))
        if observation is not None and observation.get("state") == "qualified":
            value = (observation.get("value") or {}).get("pct")
            clock = format_clock(((observation.get("clocks") or {}).get("observation")
                                  or {}).get("at"))
            if value is not None and clock is not None:
                peers.append({"id": peer_id, "name_en": peer["name_en"],
                              "name_zh": peer["name_zh"], "state": "number",
                              "qualified": True, "value_pct": value,
                              "clock": clock, "reason_pairs": None,
                              "reason_tokens": []})
                continue
        if observation is not None:
            state, reasons = "abstain", observation.get("abstain_reasons") or []
        else:
            capability = (peer["capabilities"] or {}).get("equity_index_fx") or {}
            if capability.get("display") == "qualified":
                state, reasons = "qualified", []
            else:
                state = "abstain"
                reasons = [capability.get("reason") or "no_admitted_source"]
        peers.append({"id": peer_id, "name_en": peer["name_en"],
                      "name_zh": peer["name_zh"], "state": state,
                      "qualified": False, "value_pct": None, "clock": None,
                      "reason_pairs": _reason_pairs(reasons),
                      "reason_tokens": list(reasons)})
    return peers


def build_view(*, universe, rights, contexts, workspace, observations=None):
    """One dossier panel per (horizon, basis) context the mount passes.

    Never usd_hedged (Wave 1: hedged abstains basis_unsupported and is never a
    panel context). Pure: reads only the passed documents; no IO, no store.
    """
    rows = jurisdiction_rows(universe)
    order = [row["id"] for row in rows]
    rows_by_id = {row["id"]: row for row in rows}
    index = _observation_index(observations)
    board = acceptance_matrix(universe, rights)["coverage_board"]
    board_cells = board["cells"]
    assessments = jurisdiction_assessments(universe)["claims"]
    snapshot = snapshot_display(_snapshot_clocks(observations))
    abstain_copy = {token: reason_copy(token)
                    for token in (*VIEW_ABSTAIN_TOKENS, "evidence_tier_undefined")}

    groups = []
    for key, _regions, en, zh in REGION_GROUPS:
        members = [row for row in rows
                   if row["region_group"] == key and row["kind"] == "jurisdiction"]
        groups.append({"key": key, "label_en": en, "label_zh": zh,
                       "markets": [{"id": row["id"], "name_en": row["name_en"],
                                    "name_zh": row["name_zh"]}
                                   for row in members]})
    aggregates = [row for row in rows if row["kind"] == "aggregate"]
    groups.append({"key": "aggregates", "label_en": "Aggregates", "label_zh": "聚合",
                   "markets": [{"id": row["id"], "name_en": row["name_en"],
                                "name_zh": row["name_zh"]} for row in aggregates]})

    panels = []
    for context_id, context in contexts.items():
        horizon = context["horizon"]
        basis = context["currency_basis"]
        if basis not in ("local", "usd_unhedged"):
            continue  # hedged is never a dossier context
        markets = []
        default_market = None
        for row in rows:
            observation = index.get((row["id"], horizon, basis))
            usd_observation = index.get((row["id"], horizon, "usd_unhedged"))
            capability_entry = ((universe.get("jurisdictions") or {}).get(row["id"])
                                or (universe.get("aggregates") or {}).get(row["id"])
                                or {}).get("capabilities", {}).get("equity_index_fx") or {}
            markets.append({
                "id": row["id"], "kind": row["kind"],
                "name_en": row["name_en"], "name_zh": row["name_zh"],
                "region_group": row["region_group"],
                "hero": _hero(row, observation),
                "decomposition": _decomposition(row, usd_observation),
                "clocks": _clocks(observation),
                "rights": rights_view(universe, rights, row["id"], "equity_index_fx"),
                "incumbent": (observation or {}).get("incumbent"),
                "coverage": _coverage_vector(row),
                "credit_funding": _credit_funding(row, board_cells, assessments),
                "external_vulnerability": _external_vulnerability(row, board_cells),
                "peers": _peers(row, rows_by_id, order, horizon, basis, index),
                "sources": {
                    "evidence_ref": (observation or {}).get("evidence_ref"),
                    "snapshot_clock": format_clock(
                        (observation or {}).get("snapshot_published_at")),
                    "capability_evidence_ref": capability_entry.get("evidence_ref"),
                    "capability_rights_ref": capability_entry.get("rights_ref"),
                },
            })
            if (default_market is None and row["kind"] == "jurisdiction"
                    and (usd_observation or {}).get("state") == "qualified"):
                default_market = row["id"]
        if default_market is None:
            default_market = next((row["id"] for row in rows
                                   if row["kind"] == "jurisdiction"), rows[0]["id"])
        en, zh = horizon_label(horizon)
        panels.append({
            "view": "dossier",
            "context_id": f"im-gs-dossier-{horizon}-{basis}",
            "context": {"horizon": horizon, "currency_basis": basis},
            "generation": None,
            "payload": {
                "horizon": horizon, "basis": basis,
                "horizon_label": {"id": horizon, "en": en, "zh": zh},
                "snapshot": snapshot,
                "picker_groups": groups,
                "default_market": default_market,
                "markets": markets,
                "corrections": None,
                "abstain_copy": abstain_copy,
                "evidence_tier_source": EVIDENCE_TIER_SOURCE,
            },
        })
    return panels
