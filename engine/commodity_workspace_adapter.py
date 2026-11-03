"""Read existing publications for the commodity UI; never run a collector or model.

The caller supplies its current commodity snapshot. Related artifacts retain their
own dates, including the possible one-publication lag of commodity ratio context.
Company links come exclusively from the existing Transmission/Data OS adapter.
"""
from __future__ import annotations

from copy import deepcopy
import json
import logging
from pathlib import Path

from engine.commodity_decision_workspace import build_workspace, fingerprint

log = logging.getLogger(__name__)


def read_publication(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("publisher root is not an object")
        return value
    except (OSError, ValueError) as exc:
        log.warning("Commodity workspace context unavailable: %s (%s)", path.name, type(exc).__name__)
        return None


def attach_company_continuations(workspace: dict, chain_state: dict | None, root: Path) -> dict:
    """Reuse the canonical identity proof; missing aliases produce no invented link."""
    out = deepcopy(workspace)
    if not chain_state:
        return out
    try:
        from engine.transmission_publish import derive_display_subset
        from engine.transmission_company_continuation import chain_decision_date, enrich_display_chains
        from engine.intelligence_workspace.entity import VENDOR_ALIASES, _records
        from lib.dataos.identity import VendorAliasTable

        display = derive_display_subset(chain_state)
        decision_date = chain_decision_date(display.get("asof"))
        if decision_date is None:
            return out
        try:
            aliases = VendorAliasTable.from_records(_records(root / VENDOR_ALIASES))
        except Exception as exc:  # owner adapter intentionally supports aliases=None
            log.warning("Commodity company identity unavailable (%s)", type(exc).__name__)
            aliases = None
        enriched = enrich_display_chains(display, aliases, decision_date)
        by_id = {c["id"]: c for c in enriched.get("chains", [])}
        for chain in out["chains"]:
            existing = by_id.get(chain["id"], {}).get("companies", {})
            for cohort in chain["cohorts"]:
                companies = existing.get(cohort["id"])
                if companies:
                    preview = deepcopy(companies)
                    preview["linked_count"] = len(preview.get("linked", []))
                    preview["unlinked_count"] = len(preview.get("unlinked", []))
                    preview["linked"] = preview.get("linked", [])[:6]
                    preview["unlinked"] = preview.get("unlinked", [])[:6]
                    preview["preview_only"] = True
                    preview["selection"] = "first_six_alphabetically_from_owner"
                    cohort["companies"] = preview
        out["fingerprint"] = fingerprint({"publisher_projection": workspace["fingerprint"], "company_continuations": out["chains"]})
    except Exception as exc:  # optional relationship continuation must not blank commodity data
        log.warning("Commodity company continuation unavailable (%s)", type(exc).__name__)
    return out


def workspace_from_publications(snapshot: dict, *, root: Path, data_root: Path | None = None,
                                physical_context: dict | None = None) -> dict:
    data_root = data_root if data_root is not None else root / "data"
    chains = read_publication(data_root / "transmission" / "chain_state.json")
    workspace = build_workspace(snapshot,
        transmission=read_publication(data_root / "transmission" / "latest.json"),
        fx=read_publication(data_root / "forex" / "latest.json"), chain_state=chains,
        commodity_latest=read_publication(data_root / "commodity" / "latest.json"),
        physical_context=physical_context)
    return attach_company_continuations(workspace, chains, root)
