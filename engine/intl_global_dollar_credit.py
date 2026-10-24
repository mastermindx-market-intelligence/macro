"""IM16 (INTL-GS-W3B): dollar-regime and EM credit transmission contract, v1.

Dollar and EM credit inputs as qualified-or-abstain, four-clock change
receipts built on the incumbent global-liquidity-transmission (GLT)
alignment — there is exactly one alignment in this repository and this
module adds no second one, no extra forward fill, and no staleness rule of
its own. Six closed sources: the broad dollar index, the US 10-year TIPS
real yield (both global context) and the four ICE BofA EM CORPORATE OAS
indices (regional systems). A regional or global measure never upgrades a
jurisdiction claim, which is why the per-jurisdiction assessment abstains
with a closed-vocabulary reason wherever no rights-cleared jurisdiction
source exists.

Rights facts, stated rather than assumed: no rights-matrix row names
DTWEXBGS, DFII10 or any ICE BofA series, and there is NO admitted EM
sovereign spread source — ``SOVEREIGN_SPREAD_SOURCES`` is therefore empty
by fact, not by omission, and no series, row or rights class is invented
here. The receipt discloses ``orientation`` prose instead of ever applying
the GLT ``direction_multiplier``. The minimum-history fence and the
decision-grid frequency are read from the GLT producer config at call
time, never hard-coded in this module. The frozen contagion stack (links
graph, 14-ETF VAR) is neither imported nor changed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime

import numpy as np
import pandas as pd

from engine.global_liquidity_transmission import (
    align_component,
    causal_expanding_z,
    load_producer_config,
)
from engine.intl_global_observation import (
    ABSTAIN_REASONS as OBSERVATION_ABSTAIN_REASONS,
    check_clocks,
)
from engine.intl_global_universe import CAPABILITIES, load_rights_matrix, load_universe
from engine.theme_graph.rights import EMISSION_OK
from lib import store

CONTRACT_VERSION = "intl-global-dollar-credit-v1"

#: A receipt or assessment never claims more than its source population.
CLAIM_LEVELS = ("global_context", "regional_system", "jurisdiction")

#: Closed abstain vocabulary: the IM12 observation reasons plus the six
#: dollar/credit-specific ones. Nothing outside this set may ever appear.
ABSTAIN_REASONS = frozenset(
    OBSERVATION_ABSTAIN_REASONS
    | {
        "no_admitted_source",
        "insufficient_history",
        "stale_input",
        "proxy_population_mismatch",
        "funding_observation_unavailable",
        "capability_not_qualified",
    }
)

#: Interpretation prose no receipt of this contract may ever drift from.
INTERPRETATION_LIMITS = (
    "Context input only: it describes a global or regional system, never a "
    "single jurisdiction.",
    "ICE BofA EM indices are corporate-issuer spreads, not sovereign spreads.",
    "No trading signal, sizing or recommendation.",
)


def _glt_funding_columns() -> tuple[str, str]:
    components = load_producer_config()["usd_funding_components"]
    return (components["broad_dollar"]["column"],
            components["real_yield_10y"]["column"])


_BROAD_DOLLAR_COLUMN, _REAL_YIELD_COLUMN = _glt_funding_columns()

#: The closed source table. Every ``rights_ref`` is None because no
#: rights-matrix row exists for any of these series — adding one is a
#: rights decision this contract is forbidden from making. ``column`` None
#: means the first column of the stored frame, exactly as engine/contagion.py
#: reads these keys (``df.iloc[:, 0]``).
SOURCES = {
    "broad_dollar": {
        "series_id": "DTWEXBGS",
        "store": "fred",
        "key": "DTWEXBGS",
        "column": _BROAD_DOLLAR_COLUMN,
        "glt_component": "broad_dollar",
        "claim_level": "global_context",
        "population": (
            "US dollar against a broad basket of trading-partner currencies "
            "(nominal)"),
        "unit": "index",
        "orientation": "a positive change means a stronger dollar",
        "rights_ref": None,
    },
    "us_real_yield_10y": {
        "series_id": "DFII10",
        "store": "fred",
        "key": "DFII10",
        "column": _REAL_YIELD_COLUMN,
        "glt_component": "real_yield_10y",
        "claim_level": "global_context",
        "population": "US 10-year TIPS real yield",
        "unit": "percent",
        "orientation": "a positive change means a higher real yield",
        "rights_ref": None,
    },
    "em_corporate_oas": {
        "series_id": "BAMLEMCBPIOAS",
        "store": "fred",
        "key": "BAMLEMCBPIOAS",
        "column": None,
        "glt_component": "high_yield_oas",
        "claim_level": "regional_system",
        "population": (
            "ICE BofA emerging-markets CORPORATE plus index option-adjusted "
            "spread — corporate issuers, not sovereigns"),
        "unit": "percent",
        "orientation": "a positive change means a wider spread",
        "rights_ref": None,
        "licence_note": (
            "ICE BofA data via FRED; redistribution rights unverified and no "
            "rights-matrix row"),
    },
    "em_asia_corporate_oas": {
        "series_id": "BAMLEMRACRPIASIAOAS",
        "store": "fred",
        "key": "BAMLEMRACRPIASIAOAS",
        "column": None,
        "glt_component": "high_yield_oas",
        "claim_level": "regional_system",
        "population": (
            "ICE BofA Asia emerging-markets corporate plus OAS — corporate "
            "issuers, not sovereigns"),
        "unit": "percent",
        "orientation": "a positive change means a wider spread",
        "rights_ref": None,
        "licence_note": (
            "ICE BofA data via FRED; redistribution rights unverified and no "
            "rights-matrix row"),
    },
    "em_latam_corporate_oas": {
        "series_id": "BAMLEMRLCRPILAOAS",
        "store": "fred",
        "key": "BAMLEMRLCRPILAOAS",
        "column": None,
        "glt_component": "high_yield_oas",
        "claim_level": "regional_system",
        "population": (
            "ICE BofA Latin America emerging-markets corporate plus OAS — "
            "corporate issuers, not sovereigns"),
        "unit": "percent",
        "orientation": "a positive change means a wider spread",
        "rights_ref": None,
        "licence_note": (
            "ICE BofA data via FRED; redistribution rights unverified and no "
            "rights-matrix row"),
    },
    "em_emea_corporate_oas": {
        "series_id": "BAMLEMRECRPIEMEAOAS",
        "store": "fred",
        "key": "BAMLEMRECRPIEMEAOAS",
        "column": None,
        "glt_component": "high_yield_oas",
        "claim_level": "regional_system",
        "population": (
            "ICE BofA EMEA emerging-markets corporate plus OAS — corporate "
            "issuers, not sovereigns"),
        "unit": "percent",
        "orientation": "a positive change means a wider spread",
        "rights_ref": None,
        "licence_note": (
            "ICE BofA data via FRED; redistribution rights unverified and no "
            "rights-matrix row"),
    },
}

#: Empty by fact: no rights-cleared EM sovereign spread source exists today.
#: A regional corporate index is never a sovereign spread, so nothing in
#: SOURCES may be promoted into this table.
SOVEREIGN_SPREAD_SOURCES: dict = {}

#: Direction vocabulary: (rising token, falling token) per source; an exact
#: zero change carries the ``unchanged`` token. Orientation prose in SOURCES
#: explains the token; the GLT direction multiplier is never applied.
DIRECTION_TOKENS = {
    "broad_dollar": ("dollar_stronger", "dollar_weaker"),
    "us_real_yield_10y": ("real_yield_higher", "real_yield_lower"),
    "em_corporate_oas": ("spread_wider", "spread_narrower"),
    "em_asia_corporate_oas": ("spread_wider", "spread_narrower"),
    "em_latam_corporate_oas": ("spread_wider", "spread_narrower"),
    "em_emea_corporate_oas": ("spread_wider", "spread_narrower"),
}
UNCHANGED_TOKEN = "unchanged"

#: Interpretation tokens this contract must never emit as a whole word.
BANNED_TOKENS = (
    "safe",
    "stable",
    "stability",
    "resilient",
    "crisis",
    "low_risk",
    "high_risk",
    "fragile",
)

#: The two per-jurisdiction claims v1 assesses, and the IM11 capability each
#: one reads. IM11 owns the capability vocabulary.
ASSESSMENT_CLAIMS = {
    "dollar_funding": "dollar_funding_external",
    "em_credit_sovereign": "local_rates_credit",
}

#: IM11 owns the capability vocabulary; both claims must live inside it.
_UNIVERSE_CAPABILITIES = frozenset(CAPABILITIES)
if not set(ASSESSMENT_CLAIMS.values()) <= _UNIVERSE_CAPABILITIES:
    raise ValueError(
        "ASSESSMENT_CLAIMS names a capability outside the IM11 CAPABILITIES "
        "vocabulary")


def _producer_cfg(producer_cfg) -> dict:
    return producer_cfg if producer_cfg is not None else load_producer_config()


def min_history_periods(producer_cfg=None) -> int:
    """The incumbent minimum-history fence, read at call time from GLT config."""
    return int(_producer_cfg(producer_cfg)["min_history_periods"])


def grid_frequency(producer_cfg=None) -> str:
    """The decision-grid frequency, read at call time from the GLT config."""
    return str(_producer_cfg(producer_cfg)["frequency"])


def source_spec(source_id: str, producer_cfg=None) -> dict:
    """The GLT alignment spec for one source (a deep copy; never the config).

    broad_dollar / us_real_yield_10y are the GLT usd_funding_components specs
    unchanged. Each EM corporate OAS source is the GLT high_yield_oas spec
    with only store/key/column/source_id replaced; frequency, period_anchor,
    release_lag_bdays, stale_after_calendar_days, change_transform and
    change_periods are copied from the incumbent. direction_multiplier is
    never applied anywhere in this contract.
    """
    cfg = _producer_cfg(producer_cfg)
    if source_id not in SOURCES:
        raise ValueError(
            f"unknown source_id {source_id!r}: not in the closed SOURCES table")
    meta = SOURCES[source_id]
    spec = copy.deepcopy(cfg["usd_funding_components"][meta["glt_component"]])
    if meta["column"] is None:
        spec.update({
            "store": meta["store"],
            "key": meta["key"],
            "column": None,
            "source_id": meta["series_id"],
        })
    return spec


def _clock_text(value):
    """A clock instant as text: None, ISO string, datetime or other scalar."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _date_text(value) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _receipt_identity(source_id, series_id, as_of, observation_at, evidence_ref):
    return {
        "contract_version": CONTRACT_VERSION,
        "source_id": source_id,
        "series_id": series_id,
        "as_of": _date_text(as_of),
        "observation_at": observation_at,
        "evidence_ref": evidence_ref if isinstance(evidence_ref, str) else None,
    }


def _receipt_id(identity: dict) -> str:
    encoded = json.dumps(
        identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "dc:sha256:" + hashlib.sha256(encoded).hexdigest()


def _banned_word_hits(text: str) -> list:
    hits = []
    for token in BANNED_TOKENS:
        if re.search(rf"(?<![A-Za-z0-9_]){token}(?![A-Za-z0-9_])", text):
            hits.append(token)
    return hits


def _assert_vocabulary(payload) -> None:
    """No banned interpretation token may appear as a whole word in output."""
    hits = _banned_word_hits(json.dumps(payload, default=str))
    if hits:
        raise ValueError(f"banned interpretation token(s) {hits} in a receipt")


def series_change_receipt(
    raw,
    *,
    source_id: str,
    as_of,
    ingested_at,
    computed_at,
    rights_row,
    evidence_ref,
    producer_cfg=None,
) -> dict:
    """Qualify one source's change at ``as_of`` or abstain with closed reasons.

    The incumbent GLT ``align_component`` performs the only alignment onto
    the GLT decision grid; the change at the last grid point and its
    prior-only expanding z-score follow the GLT transform config. Appending
    observations dated after ``as_of`` cannot change any output field: the
    grid ends at ``as_of``, alignment is causal and the evidence hash covers
    only rows available by ``as_of``.
    """
    cfg = _producer_cfg(producer_cfg)
    if source_id not in SOURCES:
        raise ValueError(
            f"unknown source_id {source_id!r}: not in the closed SOURCES table")
    meta = SOURCES[source_id]
    spec = source_spec(source_id, cfg)
    min_history = int(cfg["min_history_periods"])
    grid_freq = str(cfg["frequency"])

    reasons: set = set()

    grid = None
    aligned = None
    last_point = None
    has_any_value = False
    usable_at_last = False
    if raw is not None and len(raw) > 0:
        first_date = pd.DatetimeIndex(pd.to_datetime(raw.index)).min()
        grid = pd.date_range(first_date, pd.Timestamp(as_of), freq=grid_freq)
        if len(grid) > 0:
            aligned = align_component(raw, spec, grid)
            last_point = grid[-1]
            has_any_value = bool(aligned.value.notna().any())
            usable_at_last = bool(aligned.usable.loc[last_point])

    if not has_any_value:
        reasons.add("value_unavailable")
    elif not usable_at_last:
        reasons.add("stale_input")

    candidate_value = None
    if has_any_value and usable_at_last:
        level_series = aligned.value.astype(float)
        periods = int(spec["change_periods"])
        if str(spec["change_transform"]) == "log_change":
            change_series = 100.0 * np.log(level_series).diff(periods)
            change_unit = "log_pct"
        else:
            change_series = level_series.diff(periods)
            change_unit = "percentage_points"
        z_series = causal_expanding_z(change_series, min_history)
        change_at_last = float(change_series.loc[last_point])
        z_at_last = float(z_series.loc[last_point])
        prior_history = int(
            (change_series.notna() & (change_series.index < last_point)).sum())
        if (not np.isfinite(change_at_last)) or prior_history < min_history or (
                not np.isfinite(z_at_last)):
            reasons.add("insufficient_history")
        else:
            rising_token, falling_token = DIRECTION_TOKENS[source_id]
            if change_at_last == 0.0:
                direction = UNCHANGED_TOKEN
            elif change_at_last > 0.0:
                direction = rising_token
            else:
                direction = falling_token
            candidate_value = {
                "level": float(level_series.loc[last_point]),
                "change": change_at_last,
                "change_unit": change_unit,
                "change_periods": periods,
                "z_prior": z_at_last,
                "prior_history_periods": prior_history,
                "direction": direction,
            }

    rights_ref = rights_class = decision_ref = None
    if rights_row is not None:
        rights_ref = rights_row.get("id")
        rights_class = rights_row.get("rights_class")
        decision_ref = rights_row.get("decision_ref")
    if (rights_class not in EMISSION_OK
            or not (isinstance(decision_ref, str) and decision_ref.strip())):
        reasons.add("rights_unconfirmed")

    if not (isinstance(evidence_ref, str) and evidence_ref.strip()):
        reasons.add("source_evidence_missing")

    observation_at = publication_at = None
    if aligned is not None and last_point is not None and has_any_value:
        reference = aligned.reference_date.loc[last_point]
        available = aligned.available_date.loc[last_point]
        observation_at = (
            reference.strftime("%Y-%m-%d") if pd.notna(reference) else None)
        publication_at = (
            available.strftime("%Y-%m-%d") if pd.notna(available) else None)
    clocks = {
        "observation": {"at": observation_at, "precision": "session_date"},
        "source_publication": {
            "at": publication_at,
            "precision": "session_date",
            "basis": "modeled_release_lag",
        },
        "ingestion": {"at": _clock_text(ingested_at), "precision": "exact"},
        "computation": {"at": _clock_text(computed_at), "precision": "exact"},
    }
    clock_reason = check_clocks(clocks)
    if clock_reason is not None:
        reasons.add(clock_reason)

    outside = reasons - ABSTAIN_REASONS
    if outside:
        raise ValueError(
            f"abstain reasons outside the closed vocabulary: {sorted(outside)}")
    state = "qualified" if not reasons else "abstain"

    receipt = {
        "contract_version": CONTRACT_VERSION,
        "receipt_id": _receipt_id(_receipt_identity(
            source_id, meta["series_id"], as_of, observation_at, evidence_ref)),
        "source_id": source_id,
        "series_id": meta["series_id"],
        "claim_level": meta["claim_level"],
        "population": meta["population"],
        "orientation": meta["orientation"],
        "unit": meta["unit"],
        "state": state,
        "abstain_reasons": sorted(reasons),
        "value": candidate_value if state == "qualified" else None,
        "clocks": clocks,
        "alignment": {
            "frequency": spec.get("frequency"),
            "release_lag_bdays": spec.get("release_lag_bdays"),
            "stale_after_calendar_days": spec.get("stale_after_calendar_days"),
            "change_transform": spec.get("change_transform"),
            "min_history_periods": min_history,
        },
        "rights": {
            "rights_ref": rights_ref,
            "rights_class": rights_class,
            "decision_ref": decision_ref,
        },
        "evidence_ref": evidence_ref,
        "interpretation_limits": list(INTERPRETATION_LIMITS),
    }
    _assert_vocabulary(receipt)
    return receipt


def production_receipts(
    *,
    as_of,
    ingested_at,
    computed_at,
    rights_matrix=None,
    rights_rows=None,
    producer_cfg=None,
    read=store.read,
) -> dict:
    """A receipt per closed source, reading committed stores only.

    No network and no write. ``rights_rows`` (source_id -> row) overrides the
    rights-matrix lookup; otherwise the row named by the source's
    ``rights_ref`` is used, which is None for every source today. The
    evidence reference hashes exactly the rows whose modeled available date
    (reference date plus the configured business-day release lag) is on or
    before ``as_of``.
    """
    cfg = _producer_cfg(producer_cfg)
    matrix = rights_matrix if rights_matrix is not None else load_rights_matrix()
    rows = {
        row.get("id"): row
        for row in (matrix.get("rows") or [])
        if isinstance(row, dict) and row.get("id")
    }
    as_of_ts = pd.Timestamp(as_of)
    out: dict = {}
    for source_id, meta in SOURCES.items():
        spec = source_spec(source_id, cfg)
        frame = read(meta["store"], meta["key"])
        raw = None
        if frame is not None and len(frame.columns) > 0:
            column = (
                meta["column"] if meta["column"] is not None
                else frame.columns[0])
            raw = frame[column] if column in frame.columns else frame.iloc[:, 0]
        rights_row = None
        if rights_rows is not None:
            rights_row = rights_rows.get(source_id)
        elif meta["rights_ref"] is not None:
            rights_row = rows.get(meta["rights_ref"])
        evidence_ref = None
        if raw is not None and len(raw) > 0:
            lag = int(spec.get("release_lag_bdays", 0))
            available = pd.DatetimeIndex(pd.to_datetime(raw.index)) + pd.offsets.BDay(lag)
            lines = [
                f"{date:%Y-%m-%d}={value!r}"
                for date, value, avail in zip(raw.index, raw.to_numpy(), available)
                if avail <= as_of_ts
            ]
            digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
            evidence_ref = f"{meta['store']}/{meta['key']}:sha256:{digest}"
        out[source_id] = series_change_receipt(
            raw,
            source_id=source_id,
            as_of=as_of,
            ingested_at=ingested_at,
            computed_at=computed_at,
            rights_row=rights_row,
            evidence_ref=evidence_ref,
            producer_cfg=cfg,
        )
    return out


def jurisdiction_assessments(
    universe=None,
    *,
    fx_observations=None,
    broad_dollar=None,
    em_credit_receipts=None,
) -> dict:
    """Per-jurisdiction assessments for all IM11 jurisdictions; all abstain in v1.

    A context receipt, a spot FX move or even a qualified capability never
    yields a jurisdiction value: v1 has no rights-cleared jurisdiction-level
    measure for either claim, so every assessment abstains with a closed
    reason and carries the context receipt ids as references only.
    """
    doc = universe if universe is not None else load_universe()
    jurisdictions = doc.get("jurisdictions") or {}
    fx = fx_observations or {}
    if em_credit_receipts:
        receipt_iter = (
            em_credit_receipts.values()
            if isinstance(em_credit_receipts, dict)
            else em_credit_receipts)
        regional_ids = sorted(r["receipt_id"] for r in receipt_iter)
    else:
        regional_ids = []
    global_ref = (
        broad_dollar.get("receipt_id") if isinstance(broad_dollar, dict) else None)

    claims_out: dict = {}
    for claim, capability in ASSESSMENT_CLAIMS.items():
        assessments: dict = {}
        for jid in sorted(jurisdictions):
            entry = (jurisdictions[jid].get("capabilities") or {}).get(capability)
            state = entry.get("state") if isinstance(entry, dict) else None
            reason = entry.get("reason") if isinstance(entry, dict) else None
            if state == "qualified":
                reasons = {"value_unavailable"}
            elif state == "unavailable" and reason == "no_admitted_source":
                reasons = {"no_admitted_source"}
            else:
                reasons = {"capability_not_qualified"}
            if claim == "dollar_funding" and jid in fx:
                # A spot FX observation is not a funding observation; a flat
                # peg never substitutes for one either.
                reasons.add("funding_observation_unavailable")
            if claim == "em_credit_sovereign" and em_credit_receipts:
                # A regional corporate-issuer index is not a sovereign
                # jurisdiction spread.
                reasons.add("proxy_population_mismatch")
            assessments[jid] = {
                "jurisdiction": jid,
                "claim": claim,
                "capability": capability,
                "capability_state": state,
                "capability_reason": reason,
                "claim_level": "jurisdiction",
                "state": "abstain",
                "abstain_reasons": sorted(reasons),
                "global_context_ref": global_ref,
                "regional_context_refs": list(regional_ids)
                if claim == "em_credit_sovereign" else [],
                "value": None,
            }
        counts_by_reason: dict = {}
        counts_by_state: dict = {}
        for assessment in assessments.values():
            counts_by_state[assessment["state"]] = (
                counts_by_state.get(assessment["state"], 0) + 1)
            for reason in assessment["abstain_reasons"]:
                counts_by_reason[reason] = counts_by_reason.get(reason, 0) + 1
        claims_out[claim] = {
            "capability": capability,
            "jurisdictions": assessments,
            "counts_by_reason": counts_by_reason,
            "counts_by_state": counts_by_state,
        }
    output = {"contract_version": CONTRACT_VERSION, "claims": claims_out}
    _assert_vocabulary(output)
    return output
