"""engine/neuralweb/sector_map.py — Stock-to-sector/subsector mapping for sponsorship connector.

Amendment 1, Lane B2 (§C3, RUL-16).  Display-only — consumed read-only by bottom_sensors.py.

Sources (all pre-existing repo stores — no new taxonomy built):
  1. data/breadth/constituents.parquet          S&P 500 GICS sector assignments
  2. data/midcap_breadth/constituents.parquet   S&P 400 GICS sector assignments
  3. data/smallcap_breadth/constituents.parquet S&P 600 GICS sector assignments
  4. data/sector_holdings/*.parquet             SPDR sector ETF holdings (supplemental)
  5. data/baskets/membership.json              Curated theme baskets → panel_m nodes

GICS sector name → panel_s ETF node:
  Materials              → XLB
  Communication Services → XLC
  Energy                 → XLE
  Financials             → XLF
  Industrials            → XLI
  Information Technology → XLK
  Consumer Staples       → XLP
  Real Estate            → XLRE
  Utilities              → XLU
  Health Care            → XLV
  Consumer Discretionary → XLY

The legacy builder never raises and degrades sponsorship to unavailable.  The
captured-input projection rejects malformed or oversized inputs; it does not
load these stores or change the legacy sponsorship mapping.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd

from lib.dataos.identity import (
    IdentityError, IssuerMaster, VendorAliasTable, parse_id, parse_listing_key,
)

log = logging.getLogger(__name__)

# ── GICS sector name → panel_s ETF node (11 sectors) ────────────────────────
GICS_TO_ETF: dict[str, str] = {
    "Materials": "XLB",
    "Communication Services": "XLC",
    "Energy": "XLE",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Information Technology": "XLK",
    "Consumer Staples": "XLP",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Health Care": "XLV",
    "Consumer Discretionary": "XLY",
}

_SECTOR_ETFS = list(GICS_TO_ETF.values())


class SectorMapping(NamedTuple):
    """Lookup result for one ticker."""
    sector_node: str | None    # panel_s ETF node (e.g. "XLK") or None
    subsector_node: str | None  # panel_m basket node or None


_CAPTURE_POPULATIONS = frozenset({"breadth", "midcap_breadth", "smallcap_breadth"})
_CAPTURE_ATTRIBUTION_KEYS = frozenset({
    "source_ref", "raw_sha256", "source_version", "read_receipt_sha256",
    "generation_id", "captured_at", "source_effective_on", "source_available_at",
})


def _association_require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("invalid_captured_sector_associations:" + reason)


def _association_text(value: Any, maximum: int = 1024) -> str:
    _association_require(
        type(value) is str and 0 < len(value) <= maximum
        and value == value.strip() and not any(ord(c) < 32 for c in value),
        "text",
    )
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("invalid_captured_sector_associations:text_encoding") from exc
    return value


def _association_sequence(value: Any, maximum: int, reason: str) -> None:
    _association_require(type(value) in (list, tuple) and len(value) <= maximum, reason)


def _association_clock(value: Any, observed_at: datetime) -> str:
    _association_require(
        type(value) is datetime and value.tzinfo is not None
        and value.utcoffset() is not None, "aware_clock",
    )
    _association_require(value <= observed_at, "future_capture")
    return value.isoformat()


def _association_attribution(
    value: Mapping[str, Any], *, observed_at: datetime,
) -> dict[str, Any]:
    _association_require(
        isinstance(value, Mapping)
        and {"source_ref", "captured_at"} <= set(value)
        and set(value) <= _CAPTURE_ATTRIBUTION_KEYS, "attribution_shape",
    )
    out = {"source_ref": _association_text(value["source_ref"])}
    for name in ("raw_sha256", "read_receipt_sha256"):
        item = value.get(name)
        _association_require(
            item is None or type(item) is str
            and re.fullmatch(r"[0-9a-f]{64}", item) is not None, "source_digest",
        )
        out[name] = item
    for name in ("source_version", "generation_id"):
        item = value.get(name)
        out[name] = None if item is None else _association_text(item)
    _association_require(
        any(out[n] is not None for n in
            ("raw_sha256", "source_version", "read_receipt_sha256")),
        "missing_source_identity",
    )
    out["captured_at"] = _association_clock(value["captured_at"], observed_at)
    effective = value.get("source_effective_on")
    _association_require(effective is None or type(effective) is date, "effective_date")
    out["source_effective_on"] = None if effective is None else effective.isoformat()
    available = value.get("source_available_at")
    out["source_available_at"] = (
        None if available is None else _association_clock(available, value["captured_at"])
    )
    return out


def project_captured_sector_associations(
    *,
    subjects: Sequence[Mapping[str, str]],
    constituent_sources: Sequence[Mapping[str, Any]],
    alias_table: VendorAliasTable,
    issuer_records: Sequence[Mapping[str, Any]],
    identity_source: Mapping[str, Any],
    lookup_on: date,
    observed_at: datetime,
    snapshot_receipts: Sequence[Any] = (),
) -> dict[str, Any]:
    """Associate explicitly captured membership rows through native current identity.

    Pure and bounded: no loaders, holdings union, symbol normalization, acquisition,
    clock lookup, publication or policy effect.  The caller supplies the repaired
    breadth membership profile, native alias reader and captured master records.
    Attribution identifies those inputs; it does not authenticate a caller's
    assertion or promote a file version/read digest into original availability.

    lookup_on is the alias naming date, not a historical identity or classification
    cutoff.  IssuerMaster is current-only.  Unknown classification clocks stay
    unknown, and even a successful association cannot authorize current sector use,
    ETF membership, sector representativeness, causality or historical use.
    """
    _association_require(type(lookup_on) is date, "lookup_date")
    _association_clock(observed_at, observed_at)
    _association_require(lookup_on <= observed_at.date(), "future_lookup")
    _association_require(isinstance(alias_table, VendorAliasTable), "native_alias_reader")
    _association_sequence(subjects, 64, "subject_bound")
    _association_sequence(constituent_sources, 3, "source_bound")
    _association_sequence(issuer_records, 65536, "master_bound")
    _association_sequence(snapshot_receipts, 64, "snapshot_bound")
    _association_require(
        isinstance(identity_source, Mapping)
        and set(identity_source) == {"vendor_aliases", "issuer_master"},
        "identity_attribution",
    )
    attribution = [
        {"kind": kind, **_association_attribution(identity_source[kind],
                                                observed_at=observed_at)}
        for kind in ("vendor_aliases", "issuer_master")
    ]
    unique_subjects: dict[str, dict[str, str]] = {}
    for subject in subjects:
        _association_require(
            isinstance(subject, Mapping) and set(subject) == {"vendor", "vendor_symbol"}
            and subject["vendor"] == "membership", "subject_namespace",
        )
        symbol = _association_text(subject["vendor_symbol"], 128)
        unique_subjects.setdefault(symbol, {"vendor": "membership", "vendor_symbol": symbol})

    # The native constructor indexes by security ID and can overwrite duplicates.
    # Refuse those raw inputs before constructing the incumbent reader.
    master_ids: set[str] = set()
    for record in issuer_records:
        _association_require(isinstance(record, Mapping), "master_record")
        sid = _association_text(record.get("security_id"), 128)
        try:
            kind, key = parse_id(sid)
            _association_require(kind == "security" and sid == "SEC:" + key.render(),
                                 "master_security_id")
        except IdentityError as exc:
            raise ValueError("invalid_captured_sector_associations:master_security_id") from exc
        _association_require(sid not in master_ids, "duplicate_master_security")
        master_ids.add(sid)
    master = IssuerMaster.from_records(issuer_records)
    master_rows = {row.security_id: row for row in master.rows}
    bindings: dict[str, tuple[str | None, str | None, str | None, str | None]] = {}

    def bind(symbol: str) -> tuple[str | None, str | None, str | None, str | None]:
        if symbol in bindings:
            return bindings[symbol]
        reason = "ALIAS_UNAVAILABLE"
        try:
            sid = alias_table.resolve("membership", symbol, lookup_on,
                                      decision_at=observed_at,
                                      snapshot_receipts=snapshot_receipts)
            if sid is not None:
                kind, key = parse_id(sid)
                if kind != "security" or sid != "SEC:" + key.render():
                    reason = "NONCANONICAL_SECURITY"
                elif alias_table.vendor_symbol_for(
                    "membership", sid, lookup_on, decision_at=observed_at,
                    snapshot_receipts=snapshot_receipts,
                ) != symbol:
                    reason = "ALIAS_NOT_RECIPROCAL"
                elif sid not in master_rows:
                    reason = "MASTER_SECURITY_ABSENT"
                elif (master.security_state_of(sid) is not None
                      or master.superseded_by_of(sid) is not None):
                    reason = "SECURITY_NOT_ACTIVE"
                elif master_rows[sid].issuer_state != "RESOLVED":
                    reason = "ISSUER_NOT_RESOLVED"
                else:
                    issuer = master.issuer_of_security(sid)
                    listing = master.listing_key_of_security(sid)
                    if issuer is None or listing is None:
                        reason = "IDENTITY_INCOMPLETE"
                    else:
                        issuer_kind, issuer_key = parse_id(issuer)
                        listing_key = parse_listing_key(listing)
                        if (issuer_kind != "issuer" or issuer != "ISS:" + issuer_key.render()
                                or listing != listing_key.render()
                                or listing_key != key):
                            reason = "IDENTITY_INCONSISTENT"
                        else:
                            bindings[symbol] = (sid, issuer, listing, None)
                            return bindings[symbol]
        except IdentityError:
            # An explicit native refusal is not permission to inspect .rows or
            # fall back to a ticker, another namespace or the legacy map.
            reason = "NATIVE_IDENTITY_REFUSED"
        bindings[symbol] = (None, None, None, reason)
        return bindings[symbol]

    observations: list[tuple[dict[str, Any], str | None, str | None, int]] = []
    populations: set[str] = set()
    refs: set[str] = set()
    total_rows = 0
    for source in constituent_sources:
        _association_require(
            isinstance(source, Mapping)
            and {"population", "vendor", "rows"} <= set(source)
            and set(source) <= _CAPTURE_ATTRIBUTION_KEYS | {"population", "vendor", "rows"},
            "constituent_shape",
        )
        population = source["population"]
        _association_require(
            type(population) is str and population in _CAPTURE_POPULATIONS
            and population not in populations and source["vendor"] == "membership",
            "constituent_namespace",
        )
        populations.add(population)
        attr = _association_attribution(
            {k: v for k, v in source.items() if k in _CAPTURE_ATTRIBUTION_KEYS},
            observed_at=observed_at,
        )
        _association_require(attr["source_ref"] not in refs, "duplicate_source_ref")
        refs.add(attr["source_ref"])
        attribution.append({"kind": "constituents", "population": population, **attr})
        rows = source["rows"]
        _association_sequence(rows, 8192, "row_bound")
        total_rows += len(rows)
        _association_require(total_rows <= 8192, "row_bound")
        unique_rows: dict[tuple[str, str, str], int] = {}
        for row in rows:
            _association_require(
                isinstance(row, Mapping) and set(row) == {"symbol", "name", "sector"},
                "constituent_row",
            )
            native = (_association_text(row["symbol"], 128),
                      _association_text(row["name"], 512),
                      _association_text(row["sector"], 128))
            unique_rows[native] = unique_rows.get(native, 0) + 1
        for (symbol, name, sector), count in sorted(unique_rows.items()):
            sid, _issuer, _listing, reason = bind(symbol)
            observation = {
                "source_ref": attr["source_ref"], "population": population,
                "native_symbol": symbol, "native_name": name, "native_sector": sector,
                "source_effective_on": attr["source_effective_on"],
                "source_available_at": attr["source_available_at"],
                "captured_at": attr["captured_at"],
                "binding_status": "bound" if sid is not None else "unbound",
            }
            observations.append((observation, sid, reason, count - 1))

    associations = []
    for symbol, subject in unique_subjects.items():
        sid, issuer, listing, identity_reason = bind(symbol)
        selected = [
            entry for entry in observations
            if sid is not None and entry[1] == sid
            or entry[0]["native_symbol"] == symbol
        ]
        selected.sort(key=lambda e: (e[0]["source_ref"], e[0]["native_sector"],
                                     e[0]["native_name"]))
        reasons = {r for r in [identity_reason] if r is not None}
        sectors: set[str] = set()
        for observation, bound_sid, reason, _duplicates in selected:
            if reason is not None:
                reasons.add(reason)
            if sid is not None and bound_sid == sid:
                effective = observation["source_effective_on"]
                if effective is not None and effective > observed_at.date().isoformat():
                    reasons.add("CLASSIFICATION_EFFECTIVE_AFTER_OBSERVATION")
                else:
                    sectors.add(observation["native_sector"])
        sector = None
        if len(sectors) > 1:
            status = "conflict"
            reasons.add("CLASSIFICATION_CONFLICT")
        elif len(sectors) == 1 and not reasons:
            candidate = next(iter(sectors))
            if candidate in GICS_TO_ETF:
                status, sector = "available", candidate
            else:
                status = "unavailable"
                reasons.add("UNSUPPORTED_SECTOR")
        else:
            status = "unavailable"
            if not selected:
                reasons.add("NO_CAPTURED_CLASSIFICATION")
        associations.append({
            "subject": dict(subject), "status": status, "security_id": sid,
            "issuer_id": issuer, "listing_key": listing, "sector": sector,
            "sector_etf_proxy": GICS_TO_ETF[sector] if sector is not None else None,
            "etf_security_id": None, "etf_identity_status": "not_supplied",
            "source_observations": [dict(entry[0]) for entry in selected],
            "duplicate_observations_n": sum(entry[3] for entry in selected),
            "reason_codes": sorted(reasons),
        })
    counts = {status: sum(a["status"] == status for a in associations)
              for status in ("available", "unavailable", "conflict")}
    status = ("conflict" if counts["conflict"] else
              "available" if associations and counts["available"] == len(associations) else
              "partial" if counts["available"] else "unavailable")
    return {
        "schema": "sector_map.captured_associations/v1", "status": status,
        "identity_mode": "current", "lookup_on": lookup_on.isoformat(),
        "observed_at": observed_at.isoformat(),
        "coverage": {
            "requested_n": len(associations), "associated_n": counts["available"],
            "unavailable_n": counts["unavailable"], "conflict_n": counts["conflict"],
            "duplicate_requests_n": len(subjects) - len(associations),
        },
        "associations": associations,
        "source_attribution": sorted(attribution, key=lambda a: (a["kind"], a["source_ref"])),
        "limitations": {
            "current_sector_usable": False, "historically_admissible": False,
            "sector_membership_established": False,
            "sector_representativeness_established": False, "causal_claim": False,
        },
        "authority": {key: False for key in
                      ("may_rank", "may_gate", "may_size", "may_trade", "may_escalate",
                       "may_publish")},
    }


def build_sector_map(root: Path) -> dict[str, SectorMapping]:
    """Build ticker → SectorMapping from existing repo stores.

    Returns an empty dict on total failure (callers stamp sponsorship_state
    as 'unavailable' when lookup misses).

    Source priority (sector arm):
      1. data/breadth/constituents.parquet (S&P 500, 503 names)
      2. data/midcap_breadth/constituents.parquet (S&P 400, ~400 names)
      3. data/smallcap_breadth/constituents.parquet (S&P 600, ~600 names)
      4. data/sector_holdings/{ETF}.parquet (supplemental large-caps, ~220 names)
    Duplicate tickers: first hit wins (S&P 500 has the most authoritative sector
    assignments; sector_holdings is supplemental for names not in any S&P index).

    Source (subsector arm):
      data/baskets/membership.json: active members of baskets whose names appear
      as nodes in panel_m.  First basket wins per ticker.  Panel_m node set is
      the ground truth — baskets not in panel_m are ignored.
    """
    sector_map: dict[str, str] = {}   # ticker -> sector_node
    subsector_map: dict[str, str] = {}  # ticker -> subsector_node

    # ── 1. GICS breadth constituents ─────────────────────────────────────────
    breadth_paths = [
        root / "data" / "breadth" / "constituents.parquet",
        root / "data" / "midcap_breadth" / "constituents.parquet",
        root / "data" / "smallcap_breadth" / "constituents.parquet",
    ]
    for path in breadth_paths:
        if not path.exists():
            log.debug("breadth constituents not found: %s", path)
            continue
        try:
            df = pd.read_parquet(path)
            df.index.name = "symbol"
            df = df.reset_index()
            for _, row in df.iterrows():
                sym = str(row.get("symbol", "")).strip()
                sector_name = str(row.get("sector", "")).strip()
                etf = GICS_TO_ETF.get(sector_name)
                if sym and etf and sym not in sector_map:
                    sector_map[sym] = etf
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load breadth constituents %s: %s", path, exc)

    # ── 2. Sector holdings ETFs (supplemental) ───────────────────────────────
    holdings_dir = root / "data" / "sector_holdings"
    for etf in _SECTOR_ETFS:
        path = holdings_dir / f"{etf}.parquet"
        if not path.exists():
            continue
        try:
            df = pd.read_parquet(path)
            for ticker in df["ticker"].dropna().unique():
                t = str(ticker).strip()
                if t and t not in sector_map:
                    sector_map[t] = etf
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load sector holdings %s: %s", etf, exc)

    # ── 3. Baskets membership → subsector (panel_m nodes) ───────────────────
    baskets_path = root / "data" / "baskets" / "membership.json"
    if baskets_path.exists():
        try:
            with open(baskets_path) as fh:
                bdata = json.load(fh)
            baskets = bdata.get("baskets") or {}
            # We need the panel_m node set to filter relevant baskets.
            # Load it inline; if it fails we skip subsector mapping silently.
            panel_m_nodes = _load_panel_m_nodes(root)
            for basket_name, basket in baskets.items():
                if basket_name not in panel_m_nodes:
                    continue
                members = basket.get("members") or []
                for m in members:
                    if not isinstance(m, dict):
                        continue
                    ticker = (m.get("ticker") or "").strip()
                    removed = m.get("removed")
                    if ticker and not removed and ticker not in subsector_map:
                        subsector_map[ticker] = basket_name
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to load baskets membership for subsector map: %s", exc)

    # ── 4. Assemble final mapping ─────────────────────────────────────────────
    all_tickers = set(sector_map) | set(subsector_map)
    result: dict[str, SectorMapping] = {}
    for t in all_tickers:
        result[t] = SectorMapping(
            sector_node=sector_map.get(t),
            subsector_node=subsector_map.get(t),
        )

    log.info(
        "sector_map built: %d sector-mapped, %d subsector-mapped, %d total",
        len(sector_map), len(subsector_map), len(result),
    )
    return result


def _load_panel_m_nodes(root: Path) -> frozenset[str]:
    """Return the set of node names present in panel_m.  Empty frozenset on failure."""
    path = root / "data" / "oracle" / "panel_m.parquet"
    if not path.exists():
        log.debug("panel_m.parquet not found at %s", path)
        return frozenset()
    try:
        df = pd.read_parquet(path, columns=[])  # just load the index
        nodes = df.index.get_level_values("node").unique()
        return frozenset(str(n) for n in nodes)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to load panel_m nodes: %s", exc)
        return frozenset()
