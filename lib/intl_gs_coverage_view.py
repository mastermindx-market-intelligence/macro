"""IM13 coverage view builder (INTL-GS Wave 2, packet INTL-GS-W2A).

The IM16 acceptance matrix is the coverage authority for board 12 (seat
directive): the six data columns, every cell's state + reason, the per-state
legend counts and the "<cells> cells" total come from
``engine.intl_global_acceptance_matrix.acceptance_matrix(...)['coverage_board']``,
never from a local derivation. Coverage renders capability STATES and integer
jurisdiction counts — never a percentage, never a score. A clock numeral
appears in a cell only when a QUALIFIED usd_unhedged observation of this
horizon backs it (index_close / fx_fix). Specimen values never enter this
module.
"""
from __future__ import annotations

from engine.intl_global_acceptance_matrix import COVERAGE_BOARD_COLUMNS, acceptance_matrix
from lib.intl_gs_display import (
    CAPABILITY_DISPLAY,
    CAPABILITY_LABELS,
    COVERAGE_FIELDS,
    NAMES_ZH,
    REASON_COPY,
    REGION_GROUPS,
    format_clock,
    jurisdiction_rows,
)

# PROPOSAL (orchestrator gap G7, seat ruling pending): the R14 spec maps the
# six questions onto capabilities but owns no binding; W2A ships this one.
QUESTION_CAPABILITIES = {
    1: ("equity_index_fx",),
    2: ("equity_index_fx",),
    3: ("local_rates_credit", "dollar_funding_external"),
    4: ("us_exposure_transmission",),
    5: ("us_exposure_transmission",),
    6: ("equity_index_fx", "us_exposure_transmission"),
}

#: A capability is usable when at least one of its board columns is usable
#: (§7 display Complete/Qualified/Partial). Q3 reads the seat-directed column
#: set (yield_10y / cds_5y / usd_funding) directly.
_USABLE = ("complete", "qualified", "partial")
_Q3_COLUMNS = ("yield_10y", "cds_5y", "usd_funding")

EYEBROW = ("Global surveillance · Coverage", "全球监测 · 覆盖")
TITLE = ("Coverage and data states", "覆盖与数据状态")
LEDE = ("What every answer stands on: which markets reported, how fresh each "
        "source is, and what we are allowed to show.",
        "每个答案所依赖的基础：哪些市场已报告、各数据源的新鲜度，以及我们被允许展示的内容。")
MATRIX_SUB = ("Every cell is a state with a shape and a word; colour is never the only signal.",
              "每个单元格都是有形状、有文字的状态；颜色从来不是唯一的信号。")
CELLS_WORD = ("cells", "个单元格")
AGGREGATE_TITLE = ("Aggregate · not counted", "汇总 · 不计入")
SESSION_TOKEN = "session_calendar_unadmitted"
NOTHING_ADMITTED = ("Nothing admitted yet", "尚无已准入数据")
MARKETS_WORD = ("markets", "个市场")

#: board column id -> the foundation COVERAGE_FIELDS id carrying its label
_BOARD_TO_FIELD = {"index_close": "index_close", "fx_fix": "fx_fix",
                   "yield_10y": "y10", "cds_5y": "cds5y",
                   "usd_funding": "usd_funding", "us_proxy": "us_proxy"}
_FIELD_LABELS = {field[0]: (field[1], field[2]) for field in COVERAGE_FIELDS}
_CLOCK_COLUMNS = ("index_close", "fx_fix")
_VISIBLE_PER_GROUP = 5


def _pair(token):
    return REASON_COPY.get(token, (token, token))


def _legend_lines(by_state_total, cell_total):
    """Legend lines in §7 display precedence, display-state keys only."""
    precedence = ["restricted", "loading", "abstain", "stale", "suspended", "closed",
                  "corrected", "qualified", "partial", "recovered", "empty", "complete"]
    display_counts = {}
    for state, count in by_state_total.items():
        display_counts[CAPABILITY_DISPLAY[state]] = (
            display_counts.get(CAPABILITY_DISPLAY[state], 0) + count)
    return [{"display_state": display, "count": display_counts[display]}
            for display in precedence
            if display in display_counts and display_counts[display] > 0]


def _legend_lines_checked(by_state_total, cell_total):
    lines = _legend_lines(by_state_total, cell_total)
    assert sum(line["count"] for line in lines) == cell_total, \
        "state legend counts must sum to the matrix cell total"
    return lines


def _columns(board_columns):
    return [{"id": column, "label": _FIELD_LABELS[_BOARD_TO_FIELD[column]]}
            for column in board_columns]


def _cell(board_cell, clock):
    reason_token = board_cell.get("reason")
    return {
        "state": CAPABILITY_DISPLAY[board_cell["state"]],
        "reason_token": reason_token,
        "reason_copy": _pair(reason_token) if reason_token else None,
        "clock": clock,
    }


def _matrix(universe, board, columns, qualified_clocks, capability_states, linkable):
    groups = []
    rows_by_id = {}
    ez_row = None
    for group_key, regions, group_en, group_zh in REGION_GROUPS:
        group_rows, hidden_rows = [], []
        for entry in jurisdiction_rows(universe):
            if entry.get("region_group") != group_key:
                if not (group_key == "emea" and entry.get("kind") == "aggregate"):
                    continue
            board_row = board["cells"].get(entry["id"])
            if entry.get("kind") == "aggregate":
                ez_usable = [capability for capability, cap_entry in
                             (entry.get("capabilities") or {}).items()
                             if cap_entry.get("display") in _USABLE]
                ez_row = {
                    "id": entry["id"], "kind": "aggregate", "linkable": False,
                    "name_en": entry["name_en"], "name_zh": entry["name_zh"],
                    "session": None,
                    "cells": {column["id"]: {"excluded": True, "state": None,
                                             "reason_token": None, "reason_copy": None,
                                             "clock": None,
                                             "title": AGGREGATE_TITLE}
                              for column in columns},
                    "use": ez_usable,
                    "use_copy": NOTHING_ADMITTED if not ez_usable else None,
                }
                rows_by_id[entry["id"]] = ez_row
                continue
            cells = {}
            for column in columns:
                clock = qualified_clocks.get(entry["id"]) \
                    if column["id"] in _CLOCK_COLUMNS else None
                cells[column["id"]] = _cell(board_row[column["id"]], clock)
            usable = [capability for capability, cap_state in
                      (capability_states.get(entry["id"]) or {}).items()
                      if CAPABILITY_DISPLAY[cap_state] in _USABLE]
            row = {
                "id": entry["id"], "kind": "jurisdiction",
                "linkable": entry["id"] in linkable,
                "name_en": entry["name_en"], "name_zh": entry["name_zh"],
                "session": entry.get("timezone"),
                "cells": cells,
                "use": usable,
                "use_copy": NOTHING_ADMITTED if not usable else None,
            }
            rows_by_id[entry["id"]] = row
            # keep admitted markets visible even past the first rows: they are
            # the selectable ones (deep links select them); record: lane rule
            # "keep the selected market visible", server-side approximation.
            if len(group_rows) < _VISIBLE_PER_GROUP or entry["id"] in qualified_clocks:
                group_rows.append(row)
            else:
                hidden_rows.append(row)
        groups.append({"key": group_key, "label": (group_en, group_zh),
                       "count": len(group_rows) + len(hidden_rows),
                       "visible": group_rows, "hidden": hidden_rows})
    return groups, rows_by_id, ez_row


def _impact(board):
    columns_of = {capability: tuple(column for column, cap, _measure
                                    in COVERAGE_BOARD_COLUMNS if cap == capability)
                  for _column, capability, _measure in COVERAGE_BOARD_COLUMNS}
    lines = []
    for q in (1, 2, 3, 4, 5, 6):
        if q == 3:
            blocked = sum(
                1 for cells in board["cells"].values()
                if any(CAPABILITY_DISPLAY[cells[column]["state"]] not in _USABLE
                       for column in _Q3_COLUMNS))
        else:
            blocked = sum(
                1 for cells in board["cells"].values()
                if any(all(CAPABILITY_DISPLAY[cells[column]["state"]] not in _USABLE
                           for column in columns_of[capability])
                       for capability in QUESTION_CAPABILITIES[q]))
        lines.append({"q": q, "count": blocked})
    return lines


def _recovery(rights):
    lines = []
    for row in rights.get("rows") or []:
        review = row.get("review") if isinstance(row.get("review"), dict) else {}
        if (review or {}).get("status") == "confirmed":
            continue
        reason = review.get("next_action") or (review or {}).get("status") or row.get("id")
        lines.append({"id": row.get("id"), "status": (review or {}).get("status"),
                      "reason": (reason, reason)})
    return lines


def _qualified_clocks(observations, horizon):
    if not observations:
        return {}
    entries = (observations.get("bases") or {}).get("usd_unhedged") or []
    return {entry["identity"]["market_id"]: format_clock(entry["clocks"]["observation"]["at"])
            for entry in entries
            if isinstance(entry, dict)
            and entry["identity"].get("horizon") == horizon
            and entry.get("state") == "qualified"}


def _usable_capabilities(universe):
    projection = {}
    for jid, jur in (universe.get("jurisdictions") or {}).items():
        projection[jid] = {cap: (entry or {}).get("state", "unavailable")
                           for cap, entry in (jur.get("capabilities") or {}).items()}
    return projection


def build_view(*, universe, rights, contexts, workspace, observations=None):
    panels = []
    document = acceptance_matrix(universe, rights)
    board = document["coverage_board"]
    columns = _columns(board["columns"])
    capability_states = _usable_capabilities(universe)
    config = (workspace or {}).get("config") or {}
    for _context_id, context in (contexts or {}).items():
        horizon = context["horizon"]
        basis = context["currency_basis"]
        if basis not in ("local", "usd_unhedged"):
            continue
        qualified_clocks = _qualified_clocks(observations, horizon)
        groups, rows_by_id, ez_row = _matrix(universe, board, columns, qualified_clocks, capability_states, set(config.get("markets") or ()))
        payload = {
            "specimen": False,
            "horizon": {"id": horizon},
            "basis": {"id": basis},
            "header": {"eyebrow": EYEBROW, "title": TITLE, "lede": LEDE},
            "matrix": {
                "sub": MATRIX_SUB,
                "columns": columns,
                "cells_total": board["cell_total"],
                "cells_word": CELLS_WORD,
                "groups": groups,
                "rows": [row for group in groups
                         for row in group["visible"] + group["hidden"]],
                "ez_row": ez_row,
            },
            "legend": _legend_lines_checked(board["by_state_total"], board["cell_total"]),
            "impact": _impact(board),
            "impact_word": ("unavailable for", "不可用于"),
            "recovery": _recovery(rights),
            "session_title": _pair(SESSION_TOKEN),
            "markets_word": MARKETS_WORD,
        }
        panels.append(dict(view="coverage",
                           context_id=f"im-gs-coverage-{horizon}-{basis}",
                           context={"horizon": horizon, "currency_basis": basis},
                           generation=None, payload=payload))
    return panels
