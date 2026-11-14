"""Native source adapters for the industry-first Prophet research read.

Reuses stage taxonomy semantics, native industry ranks, revisions and K3E.
No collection, persistence, schedule or live selection authority is introduced.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, timedelta

import pandas as pd

from engine.prophet_industry_k3e import from_revision_frame, compose_industry_context, attach_to_candidates
from engine.stage_industry import _normalise_region
from lib.nyse_calendar import sessions_between

SCHEMA = "prophet.industry_context_read.v1"
LANES = ("buy", "watch", "leaders", "laggards", "ran")


def taxonomy_membership(taxonomy: pd.DataFrame, *, as_of: str, source_ref: str,
                        allowed_industries: set[str]) -> tuple[dict, dict[str, str], dict]:
    """Taxonomy only: never imported third-party scores or stage recommendations."""
    required = {"ticker", "region", "gics_industry"}
    if not isinstance(taxonomy, pd.DataFrame) or not required.issubset(taxonomy):
        raise ValueError("native taxonomy columns required")
    date.fromisoformat(as_of)
    if not source_ref:
        raise ValueError("taxonomy source reference required")
    frame = taxonomy[list(required)].copy()
    frame["ticker"] = frame.ticker.astype("string").str.split().str[0].str.upper()
    frame["region"] = frame.region.map(_normalise_region)
    frame = frame[(frame.region == "USA") & frame.gics_industry.isin(allowed_industries)]
    frame = frame.dropna(subset=["ticker", "gics_industry"])
    counts = frame.groupby("ticker").gics_industry.nunique()
    conflicting = sorted(counts[counts > 1].index.tolist())
    frame = frame[~frame.ticker.isin(conflicting)].drop_duplicates(["ticker", "gics_industry"])
    mapping = dict(zip(frame.ticker.astype(str), frame.gics_industry.astype(str)))
    members = [{"industry": group, "ticker": ticker} for ticker, group in sorted(mapping.items())]
    return ({"as_of": as_of, "basis": "reconstructed_static_membership", "source_ref": source_ref, "members": members}, mapping,
            {"membership_rows": len(members), "ambiguous_tickers": conflicting,
             "issuer_identity": "TICKER_PROXY_NOT_ISSUER_DEDUPLICATION", "taxonomy_only": True})


def native_industry_rows(industry_ranks: dict, *, as_of: str, source_ref: str) -> list[dict]:
    if (industry_ranks.get("schema") != "stage_industry_ranks.v1" or industry_ranks.get("asof") != as_of or not source_ref):
        raise ValueError("native industry rank envelope/date/source mismatch")
    rows = industry_ranks.get("regions", {}).get("USA")
    if not isinstance(rows, list):
        raise ValueError("native USA industry rows missing")
    output, seen = [], set()
    for row in rows:
        key = row.get("industry_id")
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("ambiguous industry identity")
        seen.add(key)
        output.append({"industry": key, "as_of": as_of, "state": str(row.get("bucket", "unmeasured")).lower(),
                       "coordinate_owner": "engine.stage_industry",
                       "coordinate_definition": "native_stage_industry_region_relative",
                       "source_ref": source_ref, "native_measurement": deepcopy(row),
                       "forecast_domain": "NOT_QUALIFIED_FOR_FRENCH49_MODEL"})
    return output


def hypothesis_read(price: dict, expectations: dict) -> dict:
    """Observed-pattern hypotheses, not additive gates or probability claims."""
    state, coverage = price.get("state", "unmeasured"), expectations.get("eps_drift_coverage")
    drift = expectations.get("median_eps_change_30d_pct")
    if expectations.get("status") != "OBSERVED_RESEARCH_CONTEXT" or drift is None:
        return {"pattern": "PRICE_CONTEXT_ONLY", "price_state": state, "expectation_coverage": coverage,
                "direction": "UNKNOWN", "question": "Does industry information confirm or contradict the price transition?",
                "research_inference_only": True}
    direction = "positive" if drift > 0 else "negative" if drift < 0 else "flat"
    patterns = {
        ("leading", "positive"): ("LEADERSHIP_WITH_POSITIVE_REVISIONS", "Test continuation versus already-priced optimism."),
        ("leading", "negative"): ("LEADERSHIP_REVISION_DIVERGENCE", "Test whether price strength survives worsening expectations."),
        ("improving", "positive"): ("RECOVERY_WITH_POSITIVE_REVISIONS", "Test durable recovery versus a late, already-priced rebound."),
        ("improving", "negative"): ("RECOVERY_DESPITE_NEGATIVE_REVISIONS", "Test early price discovery versus failed rebound; negative revisions are not an automatic veto."),
        ("lagging", "negative"): ("PRICE_AND_EXPECTATIONS_WEAK", "Test continuing impairment rather than assuming oversold means cheap."),
        ("lagging", "positive"): ("POSITIVE_REVISIONS_WITHOUT_PRICE_PARTICIPATION", "Test delayed response versus omitted adverse information."),
        ("weakening", "positive"): ("PRICE_WEAKENING_DESPITE_POSITIVE_REVISIONS", "Test expectation staleness or an already-priced peak."),
        ("weakening", "negative"): ("DETERIORATING_PRICE_AND_REVISIONS", "Test persistence of industry deterioration."),
    }
    pattern, question = patterns.get((state, direction), ("MIXED_OR_FLAT_CONTEXT", "Seek discriminating evidence, not another correlated price vote."))
    return {"pattern": pattern, "price_state": state, "direction": direction,
            "expectation_coverage": coverage, "question": question, "research_inference_only": True,
            "limitations": ["Source-dated rolling drift is not normalized K3E incorporation.",
                            "Fiscal roll, stale consensus, omitted information and taxonomy errors remain rival explanations."]}


def build_board_context(board: dict, industry_ranks: dict, taxonomy: pd.DataFrame,
                        revisions: pd.DataFrame, *, source_refs: dict[str, str],
                        k3e_inputs: dict[str, dict] | None = None) -> dict:
    """Join native rows without modifying the original board or its absent lanes."""
    as_of = board.get("as_of")
    cutoff = date.fromisoformat(as_of)
    required_refs = {"board", "industry_ranks", "taxonomy", "revisions"}
    if not required_refs.issubset(source_refs) or not all(source_refs[k] for k in required_refs):
        raise ValueError("all native input references required")
    prices = native_industry_rows(industry_ranks, as_of=as_of, source_ref=source_refs["industry_ranks"])
    members, mapping, identity = taxonomy_membership(taxonomy, as_of=as_of,
        source_ref=source_refs["taxonomy"], allowed_industries={x["industry"] for x in prices})
    sessions = sessions_between(cutoff - timedelta(days=366), cutoff)
    expectations = from_revision_frame(members, revisions, as_of=as_of, sessions=sessions, k3e_inputs=k3e_inputs)
    context = compose_industry_context(prices, expectations, as_of=as_of)
    context["source_refs"] = deepcopy(source_refs)
    for group in context["groups"].values():
        group["hypothesis"] = hypothesis_read(group["price_state"], group["expectations"])
    enriched, coverage = deepcopy(board), Counter()
    for lane in LANES:
        if lane not in board:
            continue
        original_rows = board[lane]
        if not isinstance(original_rows, list):
            continue
        new_rows = []
        for original in original_rows:
            if not isinstance(original, dict) or not isinstance(original.get("ticker"), str):
                raise ValueError("invalid native board candidate")
            temporary = {"ticker": original["ticker"], "industry": mapping.get(original["ticker"]), "as_of": as_of}
            attached = attach_to_candidates([temporary], context, as_of=as_of)[0]["industry_research_context"]
            copied = deepcopy(original)
            if "industry_research_context" in copied:
                raise ValueError("refuse replacing another context writer")
            copied["industry_research_context"] = attached
            new_rows.append(copied)
            coverage["board_rows"] += 1
            coverage["matched_industry_rows"] += int(attached["status"] == "AVAILABLE")
        enriched[lane] = new_rows
    restored = deepcopy(enriched)
    for lane in LANES:
        rows = restored.get(lane)
        if isinstance(rows, list):
            for row in rows:
                row.pop("industry_research_context", None)
    if restored != board:
        raise AssertionError("native board fields changed")
    return {"schema": SCHEMA, "as_of": as_of, "financial_influence": False,
            "authority": "research_context_only", "context": context, "board": enriched,
            "coverage": dict(coverage), "identity": identity, "preserved_native_board": True,
            "model_scope": "French49 models are not applied to unmatched GICS coordinate domains."}
