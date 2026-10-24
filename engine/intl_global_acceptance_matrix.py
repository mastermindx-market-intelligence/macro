"""IM16 (INTL-GS-W3B): the market-by-capability acceptance matrix, v1.

The masterplan requires the programme owner to adopt a market-by-capability
acceptance matrix before the IM16 freeze: which jurisdictions and regional
systems require qualified credit, dollar/funding, external-vulnerability and
US-exposure coverage; which direct or proxy measures are permitted for each
claim and at which claim level; and which gaps prevent completion. This
module IS that matrix, computed from the frozen IM11 universe rather than
asserted beside it: IM11 capability states are the only coverage authority,
a proxy satisfies a requirement only at its actual population, and missing
data stays visible without fulfilling a mandatory capability.

Counts are integer jurisdiction counts over the fixed IM11 denominator —
never a percentage, ratio, share or float anywhere in the output. The
coverage-board projection for the R14 §10.6 board can never show more
coverage than IM11 records (every board cell's STATE_RANK is at most its
capability cell's). Specimen figures in the design spec are fabricated for
layout and none of them is copied here.
"""
from __future__ import annotations

from engine.intl_global_dollar_credit import SOVEREIGN_SPREAD_SOURCES, SOURCES
from engine.intl_global_universe import (
    CAPABILITIES,
    CAPABILITY_STATES,
    STATE_RANK,
    TARGET_JURISDICTIONS,
    UniverseError,
    coverage_summary,
    load_rights_matrix,
    load_universe,
    roster_digest,
)
from engine.theme_graph.rights import EMISSION_OK

MATRIX_VERSION = "intl-im16-acceptance-matrix-v1"

#: The only capability state that satisfies an IM16 requirement.
REQUIREMENT_STATE = "qualified"

#: Capabilities every jurisdiction must carry ``qualified`` for IM16.
IM16_REQUIRED_CAPABILITIES = (
    "local_rates_credit",
    "dollar_funding_external",
    "us_exposure_transmission",
)

#: Surveillance claims -> the IM11 capability each requirement reads.
CLAIMS = {
    "em_credit": "local_rates_credit",
    "dollar_funding": "dollar_funding_external",
    "external_vulnerability": "dollar_funding_external",
    "us_exposure": "us_exposure_transmission",
}

#: The regional EM corporate OAS context sources of the dollar-credit
#: contract — regional systems, never jurisdiction measures, and none of
#: them is a rights-matrix row.
_REGIONAL_CONTEXT_SOURCE_IDS = tuple(
    source_id for source_id, meta in SOURCES.items()
    if meta.get("claim_level") == "regional_system"
)

#: Permitted direct or proxy measures per claim. A measure with
#: ``satisfies_jurisdiction_requirement`` True must be level "jurisdiction":
#: a regional or global proxy never fulfils a jurisdiction requirement. Every
#: candidate rights ref names a real rights-matrix row; an EMPTY ref list
#: means no admitted source exists for that measure today (the sovereign
#: spread), which is a gap, not a licence to invent one.
PERMITTED_MEASURES = {
    "em_credit": [
        {
            "measure": "jurisdiction_sovereign_spread",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": True,
            "candidate_rights_refs": sorted(SOVEREIGN_SPREAD_SOURCES),
        },
        {
            "measure": "local_10y_yield",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": ["fred.oecd_mirror_rates"],
        },
        {
            "measure": "regional_corporate_oas",
            "level": "regional_system",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": [],
        },
    ],
    "dollar_funding": [
        {
            "measure": "bis_imf_external_statistics",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": True,
            "candidate_rights_refs": ["bis.statistics", "imf.data"],
        },
        {
            "measure": "broad_dollar_index",
            "level": "global_context",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": [],
        },
        {
            "measure": "spot_fx",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": [
                "intl_yahoo_eod.legacy_seven_configured_index_fx_series"],
        },
    ],
    "external_vulnerability": [
        {
            "measure": "bis_imf_external_statistics",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": True,
            "candidate_rights_refs": ["bis.statistics", "imf.data"],
        },
        {
            "measure": "broad_dollar_index",
            "level": "global_context",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": [],
        },
        {
            "measure": "spot_fx",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": False,
            "candidate_rights_refs": [
                "intl_yahoo_eod.legacy_seven_configured_index_fx_series"],
        },
    ],
    "us_exposure": [
        {
            "measure": "licensed_us_exposure",
            "level": "jurisdiction",
            "satisfies_jurisdiction_requirement": True,
            "candidate_rights_refs": ["licensed_global_feed.us_exposure"],
        },
    ],
}

#: The R14 §10.6 coverage-board data columns as (column id, capability,
#: named required measure or None). A column naming a measure with no
#: admitted source is unavailable everywhere, by construction.
COVERAGE_BOARD_COLUMNS = (
    ("index_close", "equity_index_fx", None),
    ("fx_fix", "equity_index_fx", None),
    ("yield_10y", "local_rates_credit", None),
    ("cds_5y", "local_rates_credit", "jurisdiction_sovereign_spread"),
    ("usd_funding", "dollar_funding_external", None),
    ("us_proxy", "us_exposure_transmission", None),
)


def _resolve_ref(rows: dict, ref_id: str) -> dict:
    row = rows.get(ref_id)
    if row is None:
        raise UniverseError(
            f"candidate rights ref {ref_id!r} names no rights-matrix row")
    rights_class = row.get("rights_class")
    return {
        "id": ref_id,
        "rights_class": rights_class,
        "emission_ok": rights_class in EMISSION_OK,
    }


def _measure_has_no_admitted_source(measure_name: str) -> bool:
    """True when a named measure exists and admits no source at all."""
    for measures in PERMITTED_MEASURES.values():
        for measure in measures:
            if measure["measure"] == measure_name:
                return not measure["candidate_rights_refs"]
    return False


def acceptance_matrix(universe=None, rights_matrix=None) -> dict:
    """The market-by-capability acceptance matrix; pure, never mutates inputs.

    ``universe`` defaults to the frozen IM11 universe and ``rights_matrix``
    to the frozen IM11 rights matrix. Raises :class:`UniverseError` when a
    jurisdiction lacks a capability entry, carries a state outside the IM11
    vocabulary, or the roster is not the fixed denominator.
    """
    doc = universe if universe is not None else load_universe()
    matrix = rights_matrix if rights_matrix is not None else load_rights_matrix()
    rows = {
        row.get("id"): row
        for row in (matrix.get("rows") or [])
        if isinstance(row, dict) and row.get("id")
    }
    jurisdictions = doc.get("jurisdictions") or {}
    ids = sorted(jurisdictions)
    if len(ids) != TARGET_JURISDICTIONS:
        raise UniverseError(
            f"universe carries {len(ids)} jurisdictions, expected "
            f"{TARGET_JURISDICTIONS}")

    cells: dict = {}
    for jid in ids:
        capabilities = jurisdictions[jid].get("capabilities") or {}
        row_cells: dict = {}
        for capability in CAPABILITIES:
            entry = capabilities.get(capability)
            if not isinstance(entry, dict):
                raise UniverseError(
                    f"jurisdiction {jid} lacks a {capability} capability entry")
            state = entry.get("state")
            if state not in CAPABILITY_STATES:
                raise UniverseError(
                    f"jurisdiction {jid}.{capability}: state {state!r} outside "
                    f"the IM11 CAPABILITY_STATES vocabulary")
            row_cells[capability] = {
                "state": state,
                "reason": entry.get("reason"),
                "rights_ref": entry.get("rights_ref"),
            }
        cells[jid] = row_cells

    by_capability: dict = {}
    for capability in CAPABILITIES:
        by_state = {state: 0 for state in CAPABILITY_STATES}
        emission_permitted = 0
        met = 0
        for jid in ids:
            cell = cells[jid][capability]
            by_state[cell["state"]] += 1
            if cell["state"] == REQUIREMENT_STATE:
                met += 1
            ref = cell["rights_ref"]
            row = rows.get(ref) if ref else None
            if row is not None and row.get("rights_class") in EMISSION_OK:
                emission_permitted += 1
        by_capability[capability] = {
            "by_state": by_state,
            "emission_permitted": emission_permitted,
            "required_for_im16": capability in IM16_REQUIRED_CAPABILITIES,
            "met": met,
            "gap": TARGET_JURISDICTIONS - met,
        }

    by_region: dict = {}
    for jid in ids:
        region = jurisdictions[jid].get("region")
        region_block = by_region.setdefault(
            region,
            {capability: {state: 0 for state in CAPABILITY_STATES}
             for capability in CAPABILITIES})
        for capability in CAPABILITIES:
            region_block[capability][cells[jid][capability]["state"]] += 1
    by_region = {region: by_region[region] for region in sorted(by_region, key=str)}

    claims: dict = {}
    for claim, capability in CLAIMS.items():
        gap_ids_by_state: dict = {}
        gap_by_reason: dict = {}
        for jid in ids:
            cell = cells[jid][capability]
            if cell["state"] == REQUIREMENT_STATE:
                continue
            gap_ids_by_state.setdefault(cell["state"], []).append(jid)
            if cell["reason"]:
                gap_by_reason[cell["reason"]] = (
                    gap_by_reason.get(cell["reason"], 0) + 1)
        gap_ids_by_state = {
            state: sorted(jids) for state, jids in gap_ids_by_state.items()}
        permitted_measures = []
        for measure in PERMITTED_MEASURES[claim]:
            permitted_measures.append({
                "measure": measure["measure"],
                "level": measure["level"],
                "satisfies_jurisdiction_requirement": measure[
                    "satisfies_jurisdiction_requirement"],
                "candidate_rights_refs": [
                    _resolve_ref(rows, ref)
                    for ref in measure["candidate_rights_refs"]],
            })
        claims[claim] = {
            "capability": capability,
            "met": by_capability[capability]["met"],
            "gap": by_capability[capability]["gap"],
            "gap_ids_by_state": gap_ids_by_state,
            "gap_by_reason": gap_by_reason,
            "permitted_measures": permitted_measures,
        }

    board_columns = [column[0] for column in COVERAGE_BOARD_COLUMNS]
    board_cells: dict = {}
    by_column = {
        column_id: {state: 0 for state in CAPABILITY_STATES}
        for column_id in board_columns}
    for jid in ids:
        board_row: dict = {}
        for column_id, capability, measure_name in COVERAGE_BOARD_COLUMNS:
            capability_cell = cells[jid][capability]
            if (measure_name is not None
                    and _measure_has_no_admitted_source(measure_name)):
                cell = {"state": "unavailable", "reason": "no_admitted_source"}
            else:
                cell = {
                    "state": capability_cell["state"],
                    "reason": capability_cell["reason"],
                }
            if STATE_RANK[cell["state"]] > STATE_RANK[capability_cell["state"]]:
                # A board column may never show more coverage than its
                # capability; this fence makes the invariant structural.
                cell = {
                    "state": capability_cell["state"],
                    "reason": capability_cell["reason"],
                }
            board_row[column_id] = cell
            by_column[column_id][cell["state"]] += 1
        board_cells[jid] = board_row
    by_state_total = {state: 0 for state in CAPABILITY_STATES}
    for column_id in board_columns:
        for state, count in by_column[column_id].items():
            by_state_total[state] += count

    blocking = sorted(
        capability for capability in IM16_REQUIRED_CAPABILITIES
        if by_capability[capability]["gap"] > 0)

    return {
        "matrix_version": MATRIX_VERSION,
        "universe_version": doc.get("universe_version"),
        "roster_digest": roster_digest(ids),
        "measurement": "jurisdiction_count",
        "denominator": TARGET_JURISDICTIONS,
        "capabilities": list(CAPABILITIES),
        "states": list(CAPABILITY_STATES),
        "requirement_state": REQUIREMENT_STATE,
        "cells": cells,
        "by_capability": by_capability,
        "by_region": by_region,
        "claims": claims,
        "coverage_board": {
            "columns": board_columns,
            "cells": board_cells,
            "by_column": by_column,
            "cell_total": TARGET_JURISDICTIONS * len(board_columns),
            "by_state_total": by_state_total,
        },
        "im16_complete": all(
            by_capability[capability]["met"] == TARGET_JURISDICTIONS
            for capability in IM16_REQUIRED_CAPABILITIES),
        "blocking": blocking,
    }
