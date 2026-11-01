"""IM11: International Markets global universe v1 — frozen data contract tests.

The universe JSON is the frozen OUTPUT of the derivation in
``engine/intl_global_universe.py``; these tests pin the roster, the
capability-vector coverage shape (never a single percentage), the
source-rights matrix vocabulary (imported from ``engine.theme_graph.rights``,
never restated), rights isolation, and missing-data non-improvement.
"""
from __future__ import annotations

import copy
import hashlib
import re
import zoneinfo
from pathlib import Path

import pytest

import engine.intl_global_universe as igu
from engine.intl_global_universe import (
    AUTH_CLASSES,
    CAPABILITIES,
    CAPABILITY_STATES,
    MATRIX_FILE,
    ROW_FRED_MACRO,
    ROW_FRED_RATES,
    STATE_RANK,
    TARGET_JURISDICTIONS,
    UNIVERSE_FILE,
    UniverseError,
    coverage_summary,
    derive_legacy_capabilities,
    legacy_alias,
    load_eod_publication,
    load_legacy_countries,
    load_rights_matrix,
    load_universe,
    roster_digest,
    validate_against_legacy,
    validate_rights_matrix,
    validate_universe,
    withdraw_row,
)
from engine.theme_graph import rights as theme_rights

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The frozen 63-jurisdiction roster (sorted ISO 3166-1 alpha-2 ids).
FROZEN_IDS = (
    "AE", "AR", "AT", "AU", "BD", "BE", "BH", "BR", "CA", "CH", "CL", "CN",
    "CO", "CZ", "DE", "DK", "EG", "ES", "FI", "FR", "GB", "GR", "HK", "HU",
    "ID", "IE", "IL", "IN", "IR", "IS", "IT", "JP", "KE", "KR", "KW", "KZ",
    "LK", "MA", "MX", "MY", "NG", "NL", "NO", "NZ", "OM", "PE", "PH", "PK",
    "PL", "PT", "QA", "RO", "RU", "SA", "SE", "SG", "TH", "TR", "TW", "US",
    "VE", "VN", "ZA",
)
FROZEN_DIGEST = "79d3ce36c9261984a2634d3f643ac5b57d038e610e126a0e7a9c9af19798d5f4"
COHORT_COUNTS = {
    "msci_dm": 23,
    "msci_em": 24,
    "additional_classification": 3,
    "frontier_regional": 10,
    "special_handling": 3,
}
LEGACY_SIX = ("JP", "KR", "TW", "IN", "AU", "GB")
ROW_LEGACY_SERIES = "intl_yahoo_eod.legacy_seven_configured_index_fx_series"
ROW_LEGACY_HISTORY = "intl_yahoo_eod.legacy_seven_eod_history"
ALL_UNAVAILABLE = {
    "state": "unavailable",
    "reason": "no_admitted_source",
    "evidence_ref": None,
    "rights_ref": None,
}


def _flat_keys(obj):
    """Every dict key at every depth of ``obj``."""
    out = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.append(key)
            out.extend(_flat_keys(value))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_flat_keys(item))
    return out


def test_frozen_roster_and_digest():
    doc = load_universe()
    ids = sorted(doc["jurisdictions"])
    assert ids == list(FROZEN_IDS)
    assert len(ids) == TARGET_JURISDICTIONS == 63
    assert doc["target_jurisdictions"] == 63
    assert doc["roster_digest"] == FROZEN_DIGEST
    assert roster_digest(ids) == FROZEN_DIGEST
    counts: dict[str, int] = {}
    for jur in doc["jurisdictions"].values():
        counts[jur["cohort"]] = counts.get(jur["cohort"], 0) + 1
    assert counts == COHORT_COUNTS


def test_field_shapes_and_timezones():
    doc = load_universe()
    regions = {"americas", "europe", "asia_pacific", "middle_east_africa"}
    for jid, jur in doc["jurisdictions"].items():
        assert re.fullmatch(r"[A-Z]{2}", jid)
        assert jur["name"]
        assert jur["region"] in regions
        assert re.fullmatch(r"[A-Z]{3}", jur["currency"])
        zoneinfo.ZoneInfo(jur["timezone"])  # raises when the zone is invalid
        assert jur["venues"]
        for venue in jur["venues"]:
            assert re.fullmatch(r"[A-Z0-9]{4}", venue["mic"])
            assert venue["mic_register_check"]["status"] == "unverified"
            assert venue["mic_register_check"]["register_vintage"] is None


def test_exclusions_absent_from_roster():
    doc = load_universe()
    excluded = {e["id"] for e in doc["exclusions"]}
    assert excluded == {"HR", "JO", "MU", "SI", "TN"}
    assert not excluded & set(doc["jurisdictions"])
    for entry in doc["exclusions"]:
        assert entry["reason"] == "materiality_review_pending"
        assert entry["reconsider_when"]


def test_legacy_aliases_match_config():
    doc = load_universe()
    countries = load_legacy_countries()
    assert set(doc["legacy_aliases"]) == set(countries)
    ez = legacy_alias("EZ")
    assert ez == {"kind": "aggregate", "id": "EZ"}
    assert ez["id"] in doc["aggregates"]
    for key in LEGACY_SIX:
        assert legacy_alias(key) == {"kind": "jurisdiction", "id": key}
    with pytest.raises(UniverseError):
        legacy_alias("XX")


def test_capability_vector_shape():
    doc = load_universe()
    targets = dict(doc["jurisdictions"])
    targets["EZ"] = doc["aggregates"]["EZ"]
    for key, jur in targets.items():
        caps = jur["capabilities"]
        assert set(caps) == set(CAPABILITIES), key
        for cap, entry in caps.items():
            assert set(entry) == {"state", "reason", "evidence_ref", "rights_ref"}
            assert entry["state"] in CAPABILITY_STATES


def test_coverage_summary_is_a_vector_not_a_percentage():
    doc = load_universe()
    for cap in CAPABILITIES:
        summary = coverage_summary(doc, cap)
        assert summary["capability"] == cap
        assert summary["measurement"] == "jurisdiction_count"
        assert summary["denominator"] == 63
        assert set(summary["by_state"]) == set(CAPABILITY_STATES)
        assert sum(summary["by_state"].values()) == 63  # aggregates never counted
        for key in _flat_keys(summary):
            low = key.lower()
            assert not any(t in low for t in ("pct", "percent", "ratio", "share"))
    equity = coverage_summary(doc, "equity_index_fx")
    assert equity["by_state"]["delayed"] == 6
    assert equity["emission_permitted"] == 6
    # The fred/history rows feed partial states but are not EMISSION_OK, so no
    # jurisdiction may claim emission permission through them.
    for cap in ("local_rates_credit", "macro_policy", "history_pit_rights"):
        summary = coverage_summary(doc, cap)
        assert summary["emission_permitted"] == 0, cap


def test_legacy_derivation_equality_and_non_legacy_unavailable():
    doc = load_universe()
    matrix = load_rights_matrix()
    assert validate_against_legacy(
        doc, matrix, load_legacy_countries(), load_eod_publication()) == []
    non_legacy = set(doc["jurisdictions"]) - set(LEGACY_SIX)
    assert len(non_legacy) == 57
    for jid in non_legacy:
        for cap, entry in doc["jurisdictions"][jid]["capabilities"].items():
            assert entry == ALL_UNAVAILABLE, (jid, cap)


def test_rights_vocabulary_is_imported_not_restatement():
    matrix = load_rights_matrix()
    for row in matrix["rows"]:
        assert row["rights_class"] in theme_rights.RIGHTS_CLASSES
    assert matrix["vocabulary_owner"] == "engine/theme_graph/rights.py"
    # AUTH_CLASSES must equal the enum restated in config/theme_sources.yml.
    text = (REPO_ROOT / "config" / "theme_sources.yml").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if "auth_class enum:" in l)
    parsed = {p.strip() for p in line.split("auth_class enum:", 1)[1].split("|") if p.strip()}
    assert parsed == {"house", "keyless_public", "receipted_scrape", "entitled", "licensed"}
    assert AUTH_CLASSES == parsed
    assert validate_rights_matrix(matrix) == []


def test_rights_isolation():
    doc = load_universe()
    matrix = load_rights_matrix()
    # A delayed state citing a non-EMISSION_OK row must fail validation.
    mut = copy.deepcopy(doc)
    mut["jurisdictions"]["IS"]["capabilities"]["equity_index_fx"] = {
        "state": "delayed",
        "reason": "mutant",
        "evidence_ref": "config.yml#intl.countries.IS",
        "rights_ref": "intl_yahoo_eod.expanded_universe_instruments",
    }
    assert validate_universe(mut, matrix) != []
    # An EMISSION_OK row without a decision_ref must fail matrix validation.
    mmat = copy.deepcopy(matrix)
    for row in mmat["rows"]:
        if row["rights_class"] in theme_rights.EMISSION_OK:
            row["decision_ref"] = None
    assert validate_rights_matrix(mmat) != []


def test_missing_data_never_improves_a_capability():
    matrix = load_rights_matrix()
    countries = load_legacy_countries()
    for key, cfg in countries.items():
        full = derive_legacy_capabilities(key, cfg, matrix)
        for row in matrix["rows"]:
            reduced = withdraw_row(matrix, row["id"])
            derived = derive_legacy_capabilities(key, cfg, reduced)
            for cap in CAPABILITIES:
                assert STATE_RANK[derived[cap]["state"]] <= STATE_RANK[full[cap]["state"]], (
                    key, row["id"], cap)
    withdrawn = withdraw_row(matrix, ROW_LEGACY_SERIES)
    delayed = 0
    for key in LEGACY_SIX:
        derived = derive_legacy_capabilities(key, countries[key], withdrawn)
        assert derived["equity_index_fx"]["state"] != "delayed", key
        assert derived["history_pit_rights"]["state"] == "unavailable", key
        delayed += derived["equity_index_fx"]["state"] == "delayed"
    assert delayed == 0
    with pytest.raises(UniverseError):
        withdraw_row(matrix, "no.such_row")


def test_withdrawing_each_feeding_row_drops_its_capability_to_unavailable():
    # Each row below feeds exactly one capability in the derivation; removing
    # it from a deepcopy of the matrix must drop that capability to the
    # concrete all-unavailable entry for every legacy key that held more
    # (TW carries no fred yield_10y, so the rates row feeds six of seven).
    matrix = load_rights_matrix()
    countries = load_legacy_countries()
    feeds = (
        (ROW_LEGACY_HISTORY, "history_pit_rights"),
        (ROW_FRED_RATES, "local_rates_credit"),
        (ROW_FRED_MACRO, "macro_policy"),
    )
    for row_id, cap in feeds:
        reduced = copy.deepcopy(matrix)
        reduced["rows"] = [r for r in reduced["rows"] if r["id"] != row_id]
        assert len(reduced["rows"]) == len(matrix["rows"]) - 1, row_id
        held_more = 0
        for key, cfg in countries.items():
            full = derive_legacy_capabilities(key, cfg, matrix)
            if STATE_RANK[full[cap]["state"]] <= 0:
                continue
            held_more += 1
            derived = derive_legacy_capabilities(key, cfg, reduced)
            assert derived[cap] == ALL_UNAVAILABLE, (key, row_id, cap)
        assert held_more >= 6, (row_id, cap)


def test_denominators_not_frozen_and_universe_valid():
    doc = load_universe()
    den = doc["denominators"]
    assert den["capitalization"]["state"] == "not_frozen"
    assert den["turnover"]["state"] == "not_frozen"
    assert den["capitalization"]["source"] is None
    assert den["turnover"]["source"] is None
    assert den["note"]
    assert validate_universe(load_universe(), load_rights_matrix()) == []


def test_frozen_universe_invariance():
    # The module is a read-only contract surface: no write calls in source,
    # loaders leave every input file byte-identical, loads are repeatable.
    src = Path(igu.__file__).read_text(encoding="utf-8")
    for banned in ("json.dump", "yaml.dump", "yaml.safe_dump", ".write_text",
                   "'w'", '"w"', "os.remove", "unlink"):
        assert banned not in src
    watched = [REPO_ROOT / UNIVERSE_FILE, REPO_ROOT / MATRIX_FILE,
               REPO_ROOT / "config.yml"]
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in watched]
    first = load_universe()
    assert first == load_universe()
    load_rights_matrix()
    load_legacy_countries()
    load_eod_publication()
    legacy_alias("EZ")
    coverage_summary(first, "macro_policy")
    after = [hashlib.sha256(p.read_bytes()).hexdigest() for p in watched]
    assert before == after
    assert set(load_legacy_countries()) == set(LEGACY_SIX) | {"EZ"}


def test_history_row_id_is_cited_by_derivation():
    doc = load_universe()
    for key in LEGACY_SIX:
        entry = doc["jurisdictions"][key]["capabilities"]["history_pit_rights"]
        assert entry["rights_ref"] == ROW_LEGACY_HISTORY
        assert entry["evidence_ref"] == f"{MATRIX_FILE}#{ROW_LEGACY_HISTORY}"
