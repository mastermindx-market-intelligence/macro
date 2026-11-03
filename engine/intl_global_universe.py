"""International Markets global universe v1 (IM11) — frozen data contract.

Three artifacts, one vocabulary owner:

* ``config/intl_global_universe_v1.json`` — the frozen 63-jurisdiction roster.
* ``config/intl_source_rights_matrix_v1.json`` — per-source rights rows that
  REUSE the theme-graph rights vocabulary imported from
  ``engine/theme_graph.rights``; this module never mints a rights class.
* this module — loaders, the legacy capability derivation the universe JSON is
  the frozen output of, and validators (universe, rights matrix, legacy drift).

Coverage is a capability-state VECTOR over a fixed denominator, never a single
percentage: :func:`coverage_summary` emits counts only and carries no
ratio/share/percentage key anywhere. Data contract only — no collector, no
network call, no UI, and no write of any kind (the universe is frozen).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import zoneinfo
from pathlib import Path

import yaml

from engine.theme_graph.rights import EMISSION_OK, RIGHTS_CLASSES

#: The seven surveillance capabilities. A jurisdiction's coverage is a vector
#: over these, each in one of ``CAPABILITY_STATES`` — never one blended number.
CAPABILITIES: tuple[str, ...] = (
    "equity_index_fx",
    "constituent_breadth",
    "local_rates_credit",
    "dollar_funding_external",
    "macro_policy",
    "us_exposure_transmission",
    "history_pit_rights",
)

CAPABILITY_STATES: tuple[str, ...] = (
    "qualified",
    "partial",
    "delayed",
    "retained_stale",
    "market_closed",
    "suspended",
    "unavailable",
    "denied",
    "not_applicable",
)

#: Monotone rank used only for the missing-data non-improvement property:
#: withdrawing a rights row can never raise a capability's state.
STATE_RANK: dict[str, int] = {
    "qualified": 4,
    "delayed": 3,
    "partial": 2,
    "retained_stale": 2,
    "market_closed": 1,
    "suspended": 1,
    "unavailable": 0,
    "denied": 0,
    "not_applicable": 0,
}

COHORTS: tuple[str, ...] = (
    "msci_dm",
    "msci_em",
    "additional_classification",
    "frontier_regional",
    "special_handling",
)

#: Frozen cohort sizes of the v1 roster (23/24/3/10/3 = 63).
COHORT_COUNTS: dict[str, int] = {
    "msci_dm": 23,
    "msci_em": 24,
    "additional_classification": 3,
    "frontier_regional": 10,
    "special_handling": 3,
}

#: Capabilities a rights-matrix row may speak for (the seven plus reference).
ROW_CAPABILITIES: tuple[str, ...] = CAPABILITIES + ("reference",)

#: Restatement of the ``auth_class`` enum commented in config/theme_sources.yml
#: (a test pins the two together). Rights classes are NOT restated here: they
#: are imported from engine.theme_graph.rights, the single vocabulary owner.
AUTH_CLASSES: frozenset[str] = frozenset(
    {"house", "keyless_public", "receipted_scrape", "entitled", "licensed"})

TARGET_JURISDICTIONS: int = 63
UNIVERSE_FILE = "config/intl_global_universe_v1.json"
MATRIX_FILE = "config/intl_source_rights_matrix_v1.json"
CONFIG_FILE = "config.yml"

#: config.yml intl.countries is exactly the legacy seven: six jurisdictions
#: plus the EZ statistical aggregate.
LEGACY_JURISDICTION_KEYS: tuple[str, ...] = ("JP", "KR", "TW", "IN", "AU", "GB")
LEGACY_AGGREGATE_KEY = "EZ"

ROW_LEGACY_SERIES = "intl_yahoo_eod.legacy_seven_configured_index_fx_series"
ROW_LEGACY_HISTORY = "intl_yahoo_eod.legacy_seven_eod_history"
ROW_FRED_RATES = "fred.oecd_mirror_rates"
ROW_FRED_MACRO = "fred.oecd_mirror_macro"

#: The every-jurisdiction-else baseline: nothing is admitted anywhere else.
NO_ADMITTED_SOURCE = {
    "state": "unavailable",
    "reason": "no_admitted_source",
    "evidence_ref": None,
    "rights_ref": None,
}

_ROW_FIELDS = frozenset(
    {"id", "source_family", "capability", "scope", "rights_class", "auth_class",
     "decision_ref", "grant_scope", "delay", "review"})


class UniverseError(ValueError):
    """Unknown market key, unknown rights row, or unknown capability."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _rows_by_id(matrix: dict) -> dict[str, dict]:
    return {row["id"]: row for row in (matrix.get("rows") or [])
            if isinstance(row, dict) and row.get("id")}


def load_universe(path: str | Path | None = None) -> dict:
    """The frozen global universe document (read-only)."""
    p = Path(path) if path is not None else _repo_root() / UNIVERSE_FILE
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_rights_matrix(path: str | Path | None = None) -> dict:
    """The frozen source-rights matrix document (read-only)."""
    p = Path(path) if path is not None else _repo_root() / MATRIX_FILE
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_legacy_countries(path: str | Path | None = None) -> dict:
    """config.yml ``intl.countries`` — the legacy seven configured markets."""
    p = Path(path) if path is not None else _repo_root() / CONFIG_FILE
    with open(p, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    return ((doc.get("intl") or {}).get("countries")) or {}


def load_eod_publication(path: str | Path | None = None) -> dict:
    """config.yml ``intl.eod_publication`` — the Chairman EOD publication decision."""
    p = Path(path) if path is not None else _repo_root() / CONFIG_FILE
    with open(p, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    return ((doc.get("intl") or {}).get("eod_publication")) or {}


def roster_digest(ids) -> str:
    """sha256 hex of the newline-joined sorted jurisdiction ids."""
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def legacy_alias(market_key: str, universe: dict | None = None) -> dict:
    """Resolve a config.yml intl.countries key to its universe target.

    Raises :class:`UniverseError` for a key outside the legacy seven.
    """
    doc = universe if universe is not None else load_universe()
    alias = (doc.get("legacy_aliases") or {}).get(market_key)
    if alias is None:
        raise UniverseError(
            f"unknown legacy market key {market_key!r}: not in config.yml intl.countries")
    return alias


def benchmark_candidates(key: str, country_cfg: dict) -> dict:
    """The legacy_configured benchmark candidates block for one config entry."""
    return {
        "selection": "legacy_configured",
        "source": f"config.yml#intl.countries.{key}",
        "configured_series": list((country_cfg.get("indices") or {}).keys()),
        "fx": country_cfg.get("fx"),
        "fx_invert": country_cfg.get("fx_invert"),
    }


def derive_legacy_capabilities(key: str, country_cfg: dict, matrix: dict) -> dict:
    """Derive the seven-capability vector for one legacy config entry.

    The universe JSON is the frozen output of this function over config.yml's
    intl.countries (the six jurisdictions plus the EZ aggregate). Every other
    jurisdiction — including euro-area members — is all-unavailable: no member
    inherits the aggregate.
    """
    rows = _rows_by_id(matrix)
    fred = country_cfg.get("fred") or {}
    out: dict[str, dict] = {}

    series_row = rows.get(ROW_LEGACY_SERIES)
    configured = bool(country_cfg.get("index")) and bool(country_cfg.get("fx"))
    emission_ok = (
        series_row is not None
        and series_row.get("rights_class") in EMISSION_OK
        and bool(series_row.get("decision_ref")))
    if configured and emission_ok:
        out["equity_index_fx"] = {
            "state": "delayed",
            "reason": "legacy_configured_eod_t_plus_2",
            "evidence_ref": f"config.yml#intl.countries.{key}",
            "rights_ref": ROW_LEGACY_SERIES,
        }
    elif series_row is None:
        out["equity_index_fx"] = {
            "state": "unavailable",
            "reason": "no_rights_row",
            "evidence_ref": None,
            "rights_ref": None,
        }
    else:
        out["equity_index_fx"] = {
            "state": "unavailable",
            "reason": "rights_unconfirmed",
            "evidence_ref": None,
            "rights_ref": ROW_LEGACY_SERIES,
        }

    if "yield_10y" in fred and ROW_FRED_RATES in rows:
        out["local_rates_credit"] = {
            "state": "partial",
            "reason": "fred_10y_only_no_curve_or_credit",
            "evidence_ref": f"config.yml#intl.countries.{key}.fred",
            "rights_ref": ROW_FRED_RATES,
        }
    else:
        out["local_rates_credit"] = dict(NO_ADMITTED_SOURCE)

    if fred and ROW_FRED_MACRO in rows:
        out["macro_policy"] = {
            "state": "partial",
            "reason": "fred_oecd_subset",
            "evidence_ref": f"config.yml#intl.countries.{key}.fred",
            "rights_ref": ROW_FRED_MACRO,
        }
    else:
        out["macro_policy"] = dict(NO_ADMITTED_SOURCE)

    if out["equity_index_fx"]["state"] == "delayed" and ROW_LEGACY_HISTORY in rows:
        out["history_pit_rights"] = {
            "state": "partial",
            "reason": "history_retained_redistribution_scope_unresolved",
            "evidence_ref": f"{MATRIX_FILE}#{ROW_LEGACY_HISTORY}",
            "rights_ref": ROW_LEGACY_HISTORY,
        }
    else:
        out["history_pit_rights"] = dict(NO_ADMITTED_SOURCE)

    for cap in ("constituent_breadth", "dollar_funding_external",
                "us_exposure_transmission"):
        out[cap] = dict(NO_ADMITTED_SOURCE)

    return {cap: out[cap] for cap in CAPABILITIES}


def withdraw_row(matrix: dict, row_id: str) -> dict:
    """Deep copy of ``matrix`` with row ``row_id`` removed (missing-data probe).

    Raises :class:`UniverseError` when the row is absent — withdrawing a row
    that was never there is a probe of nothing.
    """
    if row_id not in _rows_by_id(matrix):
        raise UniverseError(f"unknown rights row {row_id!r}")
    out = copy.deepcopy(matrix)
    out["rows"] = [row for row in out["rows"] if row.get("id") != row_id]
    return out


def coverage_summary(universe: dict, capability: str) -> dict:
    """Coverage as a state-count vector over the fixed 63 denominator.

    Counts jurisdictions only — aggregates are never counted — and carries no
    percentage/ratio/share key at any depth.
    """
    if capability not in CAPABILITIES:
        raise UniverseError(f"unknown capability {capability!r}")
    rows = _rows_by_id(load_rights_matrix())
    by_state = {state: 0 for state in CAPABILITY_STATES}
    emission_permitted = 0
    for jur in (universe.get("jurisdictions") or {}).values():
        entry = (jur.get("capabilities") or {}).get(capability)
        if entry is None:
            continue
        state = entry.get("state")
        if state in by_state:
            by_state[state] += 1
        ref = entry.get("rights_ref")
        row = rows.get(ref) if ref else None
        if row is not None and row.get("rights_class") in EMISSION_OK:
            emission_permitted += 1
    return {
        "capability": capability,
        "measurement": "jurisdiction_count",
        "denominator": TARGET_JURISDICTIONS,
        "by_state": by_state,
        "emission_permitted": emission_permitted,
    }


def validate_rights_matrix(doc: dict) -> list[str]:
    """Errors in the rights matrix; empty means valid."""
    errors: list[str] = []
    rows = doc.get("rows") or []
    seen: set[str] = set()
    for pos, row in enumerate(rows):
        rid = str(row.get("id"))
        if rid in seen:
            errors.append(f"rights row {rid!r}: duplicate id")
        seen.add(rid)
        if set(row) != set(_ROW_FIELDS):
            errors.append(f"rights row {rid or pos}: field set is {sorted(row)}")
        if row.get("capability") not in ROW_CAPABILITIES:
            errors.append(
                f"rights row {rid}: capability {row.get('capability')!r} "
                f"outside ROW_CAPABILITIES")
        if row.get("rights_class") not in RIGHTS_CLASSES:
            errors.append(
                f"rights row {rid}: rights_class {row.get('rights_class')!r} "
                f"outside the imported RIGHTS_CLASSES")
        if row.get("auth_class") not in AUTH_CLASSES:
            errors.append(
                f"rights row {rid}: auth_class {row.get('auth_class')!r} "
                f"outside AUTH_CLASSES")
        review = row.get("review")
        if not isinstance(review, dict) or set(review) != {"status", "next_action"}:
            errors.append(f"rights row {rid}: review must be {{status, next_action}}")
        if row.get("rights_class") in EMISSION_OK and not row.get("decision_ref"):
            errors.append(
                f"rights row {rid}: an EMISSION_OK row requires a non-empty "
                f"decision_ref")
    covered = {row.get("capability") for row in rows}
    for cap in CAPABILITIES:
        if cap not in covered:
            errors.append(f"capability {cap!r} has no rights row")
    return errors


def validate_universe(doc: dict, matrix: dict) -> list[str]:
    """Structural and rights-isolation errors in the universe; empty means valid."""
    errors: list[str] = []
    rows = _rows_by_id(matrix)
    jurisdictions = doc.get("jurisdictions") or {}
    ids = sorted(jurisdictions)
    if len(ids) != TARGET_JURISDICTIONS:
        errors.append(
            f"universe carries {len(ids)} jurisdictions, "
            f"expected {TARGET_JURISDICTIONS}")
    if roster_digest(ids) != doc.get("roster_digest"):
        errors.append("roster_digest does not match sha256 of the sorted ids")
    counts = {cohort: 0 for cohort in COHORTS}
    for jid, jur in jurisdictions.items():
        cohort = jur.get("cohort")
        if cohort in counts:
            counts[cohort] += 1
        else:
            errors.append(f"jurisdiction {jid}: unknown cohort {cohort!r}")
        if not re.fullmatch(r"[A-Z]{3}", str(jur.get("currency") or "")):
            errors.append(
                f"jurisdiction {jid}: currency {jur.get('currency')!r} "
                f"is not ISO 4217-shaped")
        for venue in jur.get("venues") or []:
            if not re.fullmatch(r"[A-Z0-9]{4}", str(venue.get("mic") or "")):
                errors.append(
                    f"jurisdiction {jid}: mic {venue.get('mic')!r} "
                    f"is not ISO 10383-shaped")
        try:
            zoneinfo.ZoneInfo(str(jur.get("timezone")))
        except Exception:
            errors.append(
                f"jurisdiction {jid}: timezone {jur.get('timezone')!r} "
                f"does not load in zoneinfo")
        caps = jur.get("capabilities") or {}
        if set(caps) != set(CAPABILITIES):
            errors.append(
                f"jurisdiction {jid}: capability keys {sorted(caps)} are not "
                f"exactly the seven")
            continue
        for cap, entry in caps.items():
            state = entry.get("state")
            if state not in CAPABILITY_STATES:
                errors.append(
                    f"jurisdiction {jid}.{cap}: state {state!r} outside "
                    f"CAPABILITY_STATES")
                continue
            if state not in ("unavailable", "denied", "not_applicable"):
                if entry.get("evidence_ref") is None:
                    errors.append(
                        f"jurisdiction {jid}.{cap}: state {state} requires "
                        f"evidence_ref")
                if entry.get("rights_ref") not in rows:
                    errors.append(
                        f"jurisdiction {jid}.{cap}: rights_ref "
                        f"{entry.get('rights_ref')!r} names no matrix row")
                if state in ("qualified", "delayed", "retained_stale"):
                    row = rows.get(entry.get("rights_ref"))
                    if (row is None
                            or row.get("rights_class") not in EMISSION_OK
                            or not row.get("decision_ref")):
                        errors.append(
                            f"jurisdiction {jid}.{cap}: state {state} requires "
                            f"an EMISSION_OK rights row carrying a decision_ref")
    for cohort in COHORTS:
        if counts[cohort] != COHORT_COUNTS[cohort]:
            errors.append(
                f"cohort {cohort}: {counts[cohort]} jurisdictions, expected "
                f"{COHORT_COUNTS[cohort]}")
    excluded = {e.get("id") for e in doc.get("exclusions") or []}
    if excluded & set(ids):
        errors.append(
            f"exclusions overlap jurisdictions: {sorted(excluded & set(ids))}")
    agg = (doc.get("aggregates") or {}).get(LEGACY_AGGREGATE_KEY)
    if agg is None:
        errors.append("aggregate EZ is missing")
    else:
        missing = [m for m in agg.get("members") or [] if m not in jurisdictions]
        if missing:
            errors.append(f"aggregate EZ members outside the roster: {missing}")
        if agg.get("currency") != "EUR":
            errors.append("aggregate EZ currency is not EUR")
        if agg.get("counted_in_denominator") is not False:
            errors.append("aggregate EZ must not be counted in the denominator")
    return errors


def validate_against_legacy(doc: dict, matrix: dict, legacy_countries: dict,
                            eod_publication: dict) -> list[str]:
    """Drift between the frozen universe and the live legacy config; empty = none."""
    errors: list[str] = []
    aliases = doc.get("legacy_aliases") or {}
    if set(aliases) != set(legacy_countries):
        errors.append(
            f"legacy_aliases {sorted(aliases)} != config.yml intl.countries "
            f"{sorted(legacy_countries)}")
    jurisdictions = doc.get("jurisdictions") or {}
    for key in LEGACY_JURISDICTION_KEYS:
        cfg = legacy_countries.get(key)
        jur = jurisdictions.get(key)
        if cfg is None or jur is None:
            errors.append(f"legacy key {key} missing from config or universe")
            continue
        if jur.get("capabilities") != derive_legacy_capabilities(key, cfg, matrix):
            errors.append(
                f"{key}: stored capabilities drift from "
                f"derive_legacy_capabilities")
        if jur.get("benchmark_candidates") != benchmark_candidates(key, cfg):
            errors.append(f"{key}: benchmark_candidates do not match config.yml")
    agg = (doc.get("aggregates") or {}).get(LEGACY_AGGREGATE_KEY)
    cfg_ez = legacy_countries.get(LEGACY_AGGREGATE_KEY)
    if agg is None or cfg_ez is None:
        errors.append("aggregate EZ missing from universe or config")
    else:
        if agg.get("capabilities") != derive_legacy_capabilities(
                LEGACY_AGGREGATE_KEY, cfg_ez, matrix):
            errors.append(
                "EZ: stored capabilities drift from derive_legacy_capabilities")
        if agg.get("benchmark_candidates") != benchmark_candidates(
                LEGACY_AGGREGATE_KEY, cfg_ez):
            errors.append("EZ: benchmark_candidates do not match config.yml")
    row = _rows_by_id(matrix).get(ROW_LEGACY_SERIES)
    if row is None:
        errors.append("rights row for the legacy series is missing")
    else:
        if row.get("decision_ref") != eod_publication.get("decision_ref"):
            errors.append(
                "legacy-series decision_ref does not equal config.yml "
                "intl.eod_publication.decision_ref")
        if row.get("grant_scope") != eod_publication.get("scope"):
            errors.append(
                "legacy-series grant_scope does not equal config.yml "
                "intl.eod_publication.scope")
    return errors
