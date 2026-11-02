"""Offline unit tests for ``scripts/fif_coverage_writer.py``.

Every fixture here is synthetic: issuer identifiers and accessions are built at
runtime from small integers, specs are plain dicts, and no SEC bytes are read.
"""

from __future__ import annotations

import copy
import gzip
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import fif_coverage_writer as w

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "fif_coverage_writer.py"
SHARES = "common_shares_outstanding"
DEI_SHARES = ("dei", "EntityCommonStockSharesOutstanding")
TEN_DIGITS = re.compile(r"\b\d{10}\b")
RULE_CLOCK = "2026-10-19T12:00:00Z"


def _cik(i: int) -> str:
    return format(i, "010d")


def _accn(i: int, n: int) -> str:
    return f"{_cik(i)}-26-{n:06d}"


def _spec(metric_id, kind="instant", units=("USD",), aliases=(), deps=()):
    return {
        "metric_id": metric_id,
        "kind": kind,
        "units": tuple(units),
        "formula_dependencies": tuple(deps),
        "aliases": sorted(aliases),
    }


def _shares_spec(metric_id=SHARES, aliases=((10,) + DEI_SHARES,)):
    return _spec(metric_id, units=("shares",), aliases=aliases)


def _fact(accn, end, val=1, start=None):
    fact = {"accn": accn, "end": end, "val": val}
    if start:
        fact["start"] = start
    return fact


def _facts(*entries):
    """entries: (taxonomy, concept, unit, [facts...])"""
    out: dict = {}
    for taxonomy, concept, unit, fact_list in entries:
        units = out.setdefault(taxonomy, {}).setdefault(concept, {}).setdefault("units", {})
        units.setdefault(unit, []).extend(fact_list)
    return out


def _slot(i=1, slot_id="A1", n=1, report_date="2026-06-30", filing_date="2026-08-14", form="10-K",
          status="present", amendments=""):
    return {
        "cik": _cik(i),
        "slot_id": slot_id,
        "accession": _accn(i, n),
        "report_date": report_date,
        "filing_date": filing_date,
        "form": form,
        "slot_status": status,
        "amendments": amendments,
    }


def _own_usgaap_marker(slot):
    """A us-gaap fact from the slot's own accession (so D2 never fires)."""
    return ("us-gaap", "MarkerConcept", "USD", [_fact(slot["accession"], slot["report_date"])])


# 1. R-PERIOD -------------------------------------------------------------------


def test_r_period_instant_and_duration_bounds():
    slot = _slot()
    assets = _spec("total_assets", aliases=[(10, "us-gaap", "Assets")])
    own = slot["accession"]

    facts = _facts(("us-gaap", "Assets", "USD", [_fact(own, "2026-06-30")]))
    assert w.evaluate_cell(assets, {}, facts, slot) == {"status": "present", "reason_code": "present"}

    facts = _facts(("us-gaap", "Assets", "USD", [_fact(own, "2025-12-31")]))
    assert w.evaluate_cell(assets, {}, facts, slot)["reason_code"] == "absent_period_mismatch"

    revenue = _spec("revenue", kind="duration", aliases=[(10, "us-gaap", "Revenues")])
    # 364 inclusive days on an annual slot: 52 weeks.
    facts = _facts(("us-gaap", "Revenues", "USD", [_fact(own, "2026-06-30", start="2025-07-02")]))
    assert w.evaluate_cell(revenue, {}, facts, slot)["status"] == "present"
    # 180 inclusive days on an annual slot: not a fiscal year.
    facts = _facts(("us-gaap", "Revenues", "USD", [_fact(own, "2026-06-30", start="2026-01-02")]))
    cell = w.evaluate_cell(revenue, {}, facts, slot)
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}
    # 181-day year-to-date on an interim slot keeps the 1..400-day bound.
    interim = _slot(slot_id="I1", form="10-Q")
    facts = _facts(("us-gaap", "Revenues", "USD", [_fact(interim["accession"], "2026-06-30", start="2026-01-01")]))
    assert w.evaluate_cell(revenue, {}, facts, interim)["status"] == "present"


# 2. Formula nesting and cycles --------------------------------------------------


def test_formula_nesting_missing_leaf_and_cycle():
    slot = _slot()
    own = slot["accession"]
    specs = {
        "a": _spec("a", aliases=[(10, "us-gaap", "ConceptA")]),
        "b": _spec("b", aliases=[(10, "us-gaap", "ConceptB")]),
        "c": _spec("c", aliases=[(10, "us-gaap", "ConceptC")]),
        "mid": _spec("mid", deps=("a", "b")),
        "top": _spec("top", deps=("mid", "c")),
        "x": _spec("x", deps=("y",)),
        "y": _spec("y", deps=("x",)),
    }
    leaves = [("us-gaap", f"Concept{name}", "USD", [_fact(own, "2026-06-30")]) for name in "ABC"]
    assert w.evaluate_cell(specs["top"], specs, _facts(*leaves), slot)["status"] == "present"

    cell = w.evaluate_cell(specs["top"], specs, _facts(*leaves[:2]), slot)
    assert cell == {"status": "absent", "reason_code": "absent_dependency"}

    cell = w.evaluate_cell(specs["x"], specs, _facts(*leaves), slot)
    assert cell == {"status": "absent", "reason_code": "absent_dependency"}


# 3. Alias merge -------------------------------------------------------------------


def test_alias_merge_tries_concepts_in_priority_order():
    slot = _slot()
    own = slot["accession"]
    merged = _spec("total_assets", aliases=[(20, "us-gaap", "SecondConcept"), (10, "us-gaap", "FirstConcept")])
    assert [alias[0] for alias in merged["aliases"]] == [10, 20]

    both = _facts(
        ("us-gaap", "FirstConcept", "USD", [_fact(own, "2026-06-30", val=1)]),
        ("us-gaap", "SecondConcept", "USD", [_fact(own, "2026-06-30", val=2)]),
    )
    present, _reason, concept, _unit, priority = w.check_metric_against_facts(
        merged, both, {own}, slot_period=("2026-06-30", "A1")
    )
    assert (present, concept, priority) == (True, "FirstConcept", 10)

    second_only = _facts(("us-gaap", "SecondConcept", "USD", [_fact(own, "2026-06-30")]))
    present, _reason, concept, _unit, priority = w.check_metric_against_facts(
        merged, second_only, {own}, slot_period=("2026-06-30", "A1")
    )
    assert (present, concept, priority) == (True, "SecondConcept", 20)


# 4. D2 -------------------------------------------------------------------------------


def test_d2_missing_accession_relabels_direct_absent_metric_only():
    slot = _slot()
    other = _accn(1, 99)
    direct = _spec("total_assets", aliases=[(10, "us-gaap", "Assets")])
    formula = _spec("ratio", deps=("total_assets",))
    specs = {"total_assets": direct, "ratio": formula}
    missing = _facts(("us-gaap", "Liabilities", "USD", [_fact(other, "2025-06-30")]))

    assert w.companyfacts_missing_accession(missing, slot["accession"]) is True
    assert w.evaluate_cell(direct, specs, missing, slot) == {
        "status": "stale",
        "reason_code": "companyfacts_missing_accession",
    }
    assert w.evaluate_cell(formula, specs, missing, slot) == {
        "status": "absent",
        "reason_code": "absent_dependency",
    }

    covered = _facts(_own_usgaap_marker(slot))
    assert w.companyfacts_missing_accession(covered, slot["accession"]) is False
    assert w.evaluate_cell(direct, specs, covered, slot) == {
        "status": "absent",
        "reason_code": "absent_no_alias_fact",
    }

    for status in ("slot_absent", "fetch_failed", "not_applicable"):
        quiet = _slot(status=status)
        assert w.evaluate_cell(direct, specs, missing, quiet) == {"status": status, "reason_code": status}
    assert w.companyfacts_missing_accession(missing, "") is False


# 5. D1 strict ---------------------------------------------------------------------------


def test_d1_strict_dei_fact_at_period_end_is_plain_present():
    slot = _slot()
    facts = _facts(("dei", DEI_SHARES[1], "shares", [_fact(slot["accession"], "2026-06-30")]))
    cell = w.evaluate_cell(_shares_spec(), {}, facts, slot)
    assert cell == {"status": "present", "reason_code": "present"}
    assert not set(w.QUALIFIER_KEYS) & set(cell)


# 6. D1 qualified fallback ------------------------------------------------------------------


def _dei(slot_or_accn, *ends):
    accn = slot_or_accn["accession"] if isinstance(slot_or_accn, dict) else slot_or_accn
    return ("dei", DEI_SHARES[1], "shares", [_fact(accn, end) for end in ends])


def test_d1_fallback_qualifies_only_the_single_in_window_own_accession_instant():
    slot = _slot()
    spec = _shares_spec()
    marker = _own_usgaap_marker(slot)

    counters: dict = {}
    cell = w.evaluate_cell(spec, {}, _facts(marker, _dei(slot, "2026-07-20")), slot, counters, recorded_at=RULE_CLOCK)
    assert cell == {
        "status": "present",
        "reason_code": "present",
        "qualifier": "cover_date_as_of",
        "as_of": "2026-07-20",
        "qualifier_policy": w.qualifier_policy_ref(),
    }
    assert counters == {}

    cell = w.evaluate_cell(spec, {}, _facts(marker, _dei(slot, "2026-08-14")), slot, recorded_at=RULE_CLOCK)
    assert cell["qualifier"] == "cover_date_as_of" and cell["as_of"] == "2026-08-14"

    cell = w.evaluate_cell(spec, {}, _facts(marker, _dei(slot, "2026-08-15")), slot, recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}

    amendment = _accn(1, 2)
    amended_slot = _slot(amendments=amendment)
    cell = w.evaluate_cell(spec, {}, _facts(marker, _dei(amendment, "2026-07-20")), amended_slot,
                           recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}

    counters = {}
    cell = w.evaluate_cell(spec, {}, _facts(marker, _dei(slot, "2026-07-20", "2026-07-27")), slot, counters,
                           recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}
    assert counters == {"cover_window_ambiguous": 1}

    # W-R2 M2: identical duplicates collapse; distinct values at the date are a typed absence.
    counters = {}
    same = ("dei", DEI_SHARES[1], "shares", [_fact(slot["accession"], "2026-07-20", val=7)] * 2)
    cell = w.evaluate_cell(spec, {}, _facts(marker, same), slot, counters, recorded_at=RULE_CLOCK)
    assert cell["qualifier"] == "cover_date_as_of" and cell["as_of"] == "2026-07-20"
    assert counters == {"cover_multi_value": 1}

    counters = {}
    classes = ("dei", DEI_SHARES[1], "shares",
               [_fact(slot["accession"], "2026-07-20", val=7), _fact(slot["accession"], "2026-07-20", val=8)])
    cell = w.evaluate_cell(spec, {}, _facts(marker, classes), slot, counters, recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "cover_date_multi_class"}
    assert counters == {"cover_multi_value": 1, "cover_date_multi_class": 1}

    counters = {}
    other_metric = _shares_spec(metric_id="weighted_shares_other")
    cell = w.evaluate_cell(other_metric, {}, _facts(marker, _dei(slot, "2026-07-20")), slot, counters,
                           recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}
    assert counters == {}

    counters = {}
    no_dei = _shares_spec(aliases=[(5, "us-gaap", "CommonStockSharesOutstanding")])
    cell = w.evaluate_cell(no_dei, {}, _facts(marker, _dei(slot, "2026-07-20")), slot, counters, recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert counters == {"cover_fallback_alias_not_visible": 1}

    counters = {}
    foreign = _slot(form="20-F")
    foreign_facts = _facts(_own_usgaap_marker(foreign), _dei(foreign, "2026-07-20"))
    cell = w.evaluate_cell(spec, {}, foreign_facts, foreign, counters, recorded_at=RULE_CLOCK)
    assert "qualifier" not in cell
    assert counters == {"cover_fallback_form_not_covered": 1}


# 7. Formula strictness ---------------------------------------------------------------------


def test_formula_never_consumes_a_qualified_operand():
    slot = _slot()
    specs = {SHARES: _shares_spec(), "per_share": _spec("per_share", deps=(SHARES,))}
    counters: dict = {}
    facts = _facts(_own_usgaap_marker(slot), _dei(slot, "2026-07-20"))
    cell = w.evaluate_cell(specs["per_share"], specs, facts, slot, counters, recorded_at=RULE_CLOCK)
    assert cell == {"status": "absent", "reason_code": "absent_dependency"}
    assert counters == {"formula_blocked_by_qualified_operand": 1}


# 8. rewrite_manifest ---------------------------------------------------------------------------


def _rewrite_fixture():
    covered = _slot(1)
    interim = _slot(1, slot_id="I1", n=3, report_date="2026-03-31", filing_date="2026-05-08", form="10-Q")
    unavailable = _slot(2)
    specs = {
        "total_assets": _spec("total_assets", aliases=[(10, "us-gaap", "Assets")]),
        SHARES: _shares_spec(),
        "revenue": _spec("revenue", kind="duration", aliases=[(10, "us-gaap", "Revenues")]),
    }

    def cell(slot, field_id, status, reason, **extra):
        out = {
            "cik": slot["cik"],
            "period_id": slot["slot_id"],
            "field_id": field_id,
            "accession": slot["accession"],
            "tier": "core",
            "cell_id": f"{slot['cik']}:{slot['slot_id']}:{field_id}",
            "status": status,
            "reason_code": reason,
        }
        out.update(extra)
        return out

    base = {
        "schema": "synthetic.coverage_manifest/v0",
        "recorded_at": "2026-01-01T00:00:00Z",
        "cells": [
            cell(covered, "package.primary", "present", "present"),
            cell(covered, "metric:total_assets", "absent", "absent_no_alias_fact",
                 qualifier="cover_date_as_of", as_of="2026-07-01", qualifier_policy="stale"),
            cell(covered, f"metric:{SHARES}", "absent", "absent_period_mismatch"),
            cell(interim, "metric:revenue", "absent", "absent_no_alias_fact"),
            cell(unavailable, "metric:total_assets", "absent", "absent_no_alias_fact"),
        ],
        "issuers": [
            {"cik": covered["cik"], "tier_assigned": "core", "present_cells": 0},
            {"cik": unavailable["cik"], "tier_assigned": "core", "present_cells": 0},
        ],
    }
    facts = _facts(
        ("us-gaap", "Assets", "USD", [_fact(covered["accession"], "2026-06-30")]),
        _dei(covered, "2026-07-20"),
        _own_usgaap_marker(interim),
    )
    by_cik = {covered["cik"]: facts}
    provenance = {"mapping_rule_ids": ["rule.synthetic/v1"], "catalog_version": "9.9.9",
                  "mapping_pack_version": "9.9.9", "base_manifest_sha256": "0" * 64}
    return base, [covered, interim, unavailable], by_cik.get, specs, provenance


def _check_rewrite():
    base, slots, loader, specs, provenance = _rewrite_fixture()
    frozen = copy.deepcopy(base)
    recorded_at = "2026-10-19T12:00:00Z"
    manifest, counts = w.rewrite_manifest(base, slots, loader, specs, recorded_at, provenance)
    assert base == frozen

    cells = manifest["cells"]
    assert cells[0] == base["cells"][0]
    for old, new in zip(base["cells"], cells):
        for key in ("cik", "period_id", "field_id", "accession", "tier", "cell_id"):
            assert new[key] == old[key]
    assert cells[1] == {**{k: v for k, v in base["cells"][1].items() if k not in w.QUALIFIER_KEYS},
                        "status": "present", "reason_code": "present"}
    assert cells[2]["qualifier"] == "cover_date_as_of" and cells[2]["as_of"] == "2026-07-20"
    assert cells[3]["status"] == "absent" and cells[3]["reason_code"] == "absent_no_alias_fact"
    assert cells[4] == base["cells"][4]

    covered, unavailable = manifest["issuers"]
    # Core issuer: A1 total_assets (strict) + A1 shares (qualified) present; I1 revenue absent;
    # the package cell is deep-only and is not counted for a core issuer.
    assert (covered["present_cells"], covered["absent_cells"], covered["na_cells"]) == (2, 1, 0)
    assert covered["core_pass"] is False and covered["deep_pass"] is False
    assert (unavailable["present_cells"], unavailable["absent_cells"]) == (0, 1)

    assert manifest["recorded_at"] == recorded_at
    writer = manifest["writer"]
    assert writer["schema"] == w.WRITER_SCHEMA
    assert "latest practicable date" in writer["policy"]["reason"]
    assert writer["rules_recorded_at"] == recorded_at
    assert writer["mapping_rule_ids"] == ["rule.synthetic/v1"]

    assert counts["cells_rewritten"] == 3
    assert counts["facts_unavailable_issuers"] == 1
    assert counts["present_strict"] == {"all": 1, "core": 1}
    assert counts["present_qualified"] == {"all": 1, "core": 1}
    assert counts["by_reason"]["core"] == {"present/present": 2, "absent/absent_no_alias_fact": 1}

    again, _ = w.rewrite_manifest(*_rewrite_fixture()[:4], recorded_at, provenance)
    assert w.dump_manifest(again) == w.dump_manifest(manifest)
    return manifest


def test_rewrite_manifest_preserves_identity_and_recomputes_rollups():
    _check_rewrite()


def test_rewrite_manifest_guards_count_and_keep_cells():
    base, slots, loader, specs, provenance = _rewrite_fixture()
    base["cells"].append({**base["cells"][1], "field_id": "metric:not_in_bundle"})
    base["cells"].append({**base["cells"][1], "period_id": "Z9"})
    base["cells"].append({**base["cells"][1], "accession": _accn(1, 77)})
    manifest, counts = w.rewrite_manifest(base, slots, loader, specs, "2026-10-19T12:00:00Z", provenance)
    assert manifest["cells"][-3:] == base["cells"][-3:]
    assert (counts["metric_not_visible"], counts["slot_row_missing"], counts["slot_accession_mismatch"]) == (1, 1, 1)


# 9. Rollups derived by hand ----------------------------------------------------------------------


def test_rollups_match_hand_derivation():
    metric_ids = ["m1", "m2"]
    core_cells = [
        ("A1", "metric:m1", "present"),
        ("I1", "metric:m1", "present"),
        ("A1", "metric:m2", "not_applicable"),
        ("I1", "metric:m2", "present"),
        ("A2", "metric:m1", "absent"),  # orphan period for a core member
        ("A1", "package.primary", "present"),  # deep-only field on a core member
        ("*", "metric:m1", "absent"),
        ("*", "packet", "present"),  # windowless, deep-only
    ]
    # Core: counted = A1 m1, I1 m1, I1 m2 (present) and A1 m2 (n/a) -> (3, 0, 1); the core
    # window has 3 applicable cells, all present -> core_pass True; deep_pass False (not deep).
    assert w._count_rollup_cells(core_cells, "core") == (3, 0, 1)
    assert w._window_pass(core_cells, "core", w.CORE_WINDOW_SLOTS, metric_ids) is True
    assert w._deep_pass(core_cells, "core", metric_ids) is False

    deep_cells = [
        ("A1", "metric:m1", "present"),
        ("A1", "metric:m2", "not_applicable"),
        ("A2", "metric:m1", "absent"),
        ("A2", "metric:m2", "present"),
        ("I1", "metric:m1", "present"),
        ("I1", "metric:m2", "present"),
        ("I2", "metric:m1", "present"),
        ("I2", "metric:m2", "slot_absent"),
        ("A1", "package.primary", "present"),
        ("*", "packet", "present"),
        ("Q9", "metric:m1", "present"),  # orphan period: outside the deep window
    ]
    # Deep: present = A1 m1, A2 m2, I1 m1, I1 m2, I2 m1, package.primary, packet = 7;
    # absent = A2 m1 (absent) + I2 m2 (slot_absent) = 2; n/a = A1 m2 = 1.
    # Core window (A1, I1): 3 applicable, all present -> True.  Deep window fails on A2 m1.
    assert w._count_rollup_cells(deep_cells, "deep") == (7, 2, 1)
    assert w._window_pass(deep_cells, "deep", w.CORE_WINDOW_SLOTS, metric_ids) is True
    assert w._window_pass(deep_cells, "deep", w.DEEP_WINDOW_SLOTS, metric_ids) is False
    assert w._deep_pass(deep_cells, "deep", metric_ids) is False


# 10. Registry smoke ---------------------------------------------------------------------------------


def test_registry_specs_at_a_recorded_clock():
    specs, provenance = w.metric_specs_at(ROOT, "2026-10-19T00:00:00Z")
    assert specs and provenance["mapping_rule_ids"] == sorted(provenance["mapping_rule_ids"])
    for spec in specs.values():
        assert spec["kind"] in {"instant", "duration"}
        assert spec["aliases"] == sorted(spec["aliases"])
    assert DEI_SHARES in {(taxonomy, concept) for _p, taxonomy, concept in specs[SHARES]["aliases"]}
    with pytest.raises(ValueError):
        w.metric_specs_at(ROOT, "2026-08-01T00:00:00Z")


# 11. Offline ----------------------------------------------------------------------------------------------


def test_rewrite_runs_with_sockets_disabled(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    _check_rewrite()


def test_sources_carry_no_network_import_clock_or_identifier_literal():
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(r"^\s*(?:import|from)\s+(urllib|requests|http|socket|aiohttp|subprocess)\b", re.M)
    assert forbidden.search(source) is None
    assert "datetime.now" not in source and "time.time" not in source
    assert TEN_DIGITS.search(source) is None
    assert TEN_DIGITS.search(Path(__file__).read_text(encoding="utf-8")) is None


# CLI round trip over a synthetic cache -----------------------------------------------------------------


def test_cli_rewrite_is_byte_identical_across_runs(tmp_path, capsys):
    base, slots, loader, _specs, _provenance = _rewrite_fixture()
    cache = tmp_path / "cache"
    cache.mkdir()
    for cik in {slot["cik"] for slot in slots}:
        facts = loader(cik)
        if facts is not None:
            payload = json.dumps({"facts": facts}).encode("utf-8")
            (cache / f"{w.companyfacts_cache_key(cik)}.gz").write_bytes(gzip.compress(payload, mtime=0))
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps(base), encoding="utf-8")
    slots_path = tmp_path / "slots.csv"
    header = list(slots[0])
    slots_path.write_text(
        ",".join(header) + "\n" + "".join(",".join(slot[k] for k in header) + "\n" for slot in slots),
        encoding="utf-8",
    )
    outputs = []
    for name in ("one.json", "two.json"):
        out = tmp_path / name
        assert w.main([
            "rewrite", "--base-manifest", str(base_path), "--slots", str(slots_path),
            "--facts-cache", str(cache), "--recorded-at", "2026-10-19T00:00:00Z", "--out", str(out),
            "--repo-root", str(ROOT),
        ]) == 0
        printed = json.loads(capsys.readouterr().out)
        outputs.append(out.read_bytes())
        assert printed["facts_unavailable_issuers"] == 1
        assert printed["present_qualified"]["all"] == 1
    assert outputs[0] == outputs[1]
    written = json.loads(outputs[0])
    assert written["writer"]["catalog_version"] and written["writer"]["base_manifest_sha256"]


# W-R2 M1: strict-only issuer rollups ---------------------------------------------------------------------


def test_strict_rollups_exclude_qualified_present_cells():
    annual = _slot(1)
    interim = _slot(1, slot_id="I1", n=3, report_date="2026-03-31", filing_date="2026-05-08", form="10-Q")
    specs = {"total_assets": _spec("total_assets", aliases=[(10, "us-gaap", "Assets")]), SHARES: _shares_spec()}

    def cell(slot, metric_id):
        return {"cik": slot["cik"], "period_id": slot["slot_id"], "field_id": f"metric:{metric_id}",
                "accession": slot["accession"], "tier": "core", "status": "absent",
                "reason_code": "absent_no_alias_fact"}

    base = {
        "cells": [cell(slot, metric_id) for slot in (annual, interim) for metric_id in sorted(specs)],
        "issuers": [{"cik": annual["cik"], "tier_assigned": "core"}],
    }
    facts = _facts(
        ("us-gaap", "Assets", "USD",
         [_fact(annual["accession"], annual["report_date"]), _fact(interim["accession"], interim["report_date"])]),
        _dei(interim, interim["report_date"]),  # strict: the interim period end
        _dei(annual, "2026-07-20"),  # qualified: the annual cover date
    )
    manifest, counts = w.rewrite_manifest(base, [annual, interim], {annual["cik"]: facts}.get, specs, RULE_CLOCK, {})
    (issuer,) = manifest["issuers"]
    assert issuer["core_pass"] is True and issuer["core_pass_strict"] is False
    assert issuer["present_cells"] == 4 and issuer["present_cells_strict"] == 3
    assert issuer["deep_pass"] is False and issuer["deep_pass_strict"] is False
    assert counts["issuer_rollups"] == {
        "any_basis": {"core_pass": 1, "deep_pass": 0, "present_cells": 4},
        "strict": {"core_pass_strict": 0, "deep_pass_strict": 0, "present_cells_strict": 3},
    }
    assert manifest["writer"]["rollup_basis"] == {
        "present_cells": "any_basis", "core_pass": "any_basis", "deep_pass": "any_basis",
        "present_cells_strict": "strict", "core_pass_strict": "strict", "deep_pass_strict": "strict",
    }

    plain = {"status": "present", "reason_code": "present"}
    assert w._strict_status(plain) == "present"
    assert w._strict_status({**plain, "qualifier": "cover_date_as_of"}) == "present_labelled"
    assert w._strict_status({**plain, "derivation": "composed"}) == "present_labelled"
    assert w._strict_status({**plain, "qualifier": None}) == "present"
    assert w._strict_status({"status": "absent", "qualifier": "cover_date_as_of"}) == "absent"
    assert w._is_labelled({"derivation": "composed"}) is True
    assert w._is_labelled({"qualifier": None, "derivation": None}) is False
    assert w.REEVALUATED_KEYS == (*w.QUALIFIER_KEYS, "derivation")


# N1: a re-evaluated cell drops a stale derivation; one strict predicate everywhere ----------------


def test_rewrite_clears_stale_derivation_and_counts_strict_with_one_predicate():
    annual = _slot(1)
    specs = {"total_assets": _spec("total_assets", aliases=[(10, "us-gaap", "Assets")]), SHARES: _shares_spec()}

    def cell(field_id, status, reason):
        return {"cik": annual["cik"], "period_id": annual["slot_id"], "field_id": field_id,
                "accession": annual["accession"], "tier": "core", "status": status, "reason_code": reason,
                "derivation": "composed"}

    base = {
        "cells": [
            cell("metric:total_assets", "present", "present"),
            cell(f"metric:{SHARES}", "absent", "absent_no_alias_fact"),
            cell("package.primary", "present", "present"),
        ],
        "issuers": [{"cik": annual["cik"], "tier_assigned": "core"}],
    }
    facts = _facts(
        ("us-gaap", "Assets", "USD", [_fact(annual["accession"], annual["report_date"])]),
        _dei(annual, "2026-07-20"),  # only the annual cover date: a qualified present
    )

    def derived_metric_cells(cells):
        return sum(1 for c in cells if str(c["field_id"]).startswith("metric:") and c.get("derivation") is not None)

    assert derived_metric_cells(base["cells"]) == 2
    manifest, counts = w.rewrite_manifest(base, [annual], {annual["cik"]: facts}.get, specs, RULE_CLOCK, {})
    assert derived_metric_cells(manifest["cells"]) == 0

    by_field = {c["field_id"]: c for c in manifest["cells"]}
    assert by_field["package.primary"]["derivation"] == "composed"
    assets = by_field["metric:total_assets"]
    assert assets["status"] == "present" and "derivation" not in assets
    assert w._strict_status(assets) == "present"
    shares = by_field[f"metric:{SHARES}"]
    assert shares["status"] == "present" and shares.get("qualifier") is not None
    assert w._strict_status(shares) == "present_labelled"

    assert counts["present_strict"]["all"] == 1
    assert counts["present_qualified"]["all"] == 1
    (issuer,) = manifest["issuers"]
    assert issuer["present_cells"] == 2
    assert issuer["present_cells_strict"] == 1
    assert issuer["present_cells_strict"] == counts["present_strict"]["all"]


# W-R2 M3: the strict alias search never leaves the alias's own taxonomy -----------------------------------


def test_strict_alias_search_never_crosses_taxonomy():
    slot = _slot(form="20-F")
    own = slot["accession"]
    assets = _spec("total_assets", aliases=[(10, "us-gaap", "Assets")])
    dei_own = _dei(slot, "2026-07-20")

    ifrs_only = _facts(("ifrs-full", "Assets", "USD", [_fact(own, "2026-06-30")]), dei_own)
    present, reason, *_rest = w.check_metric_against_facts(assets, ifrs_only, {own}, slot_period=("2026-06-30", "A1"))
    assert (present, reason) == (False, "absent_other_taxonomy_only")
    assert w.evaluate_cell(assets, {}, ifrs_only, slot) == {
        "status": "absent", "reason_code": "absent_other_taxonomy_only"}

    elsewhere = _facts(("ifrs-full", "Assets", "USD", [_fact(_accn(1, 50), "2026-06-30")]), dei_own)
    assert w.evaluate_cell(assets, {}, elsewhere, slot) == {"status": "absent", "reason_code": "absent_no_alias_fact"}


# W-R2 M4: D2 needs the accession missing from every taxonomy -----------------------------------------------


def test_d2_requires_the_accession_missing_from_every_taxonomy():
    slot = _slot(form="20-F")
    own = slot["accession"]
    revenue = _spec("revenue", kind="duration", aliases=[(10, "us-gaap", "Revenues")])
    probe = _facts(
        ("ifrs-full", "Revenue", "USD", [_fact(own, "2026-06-30", start="2025-07-02")]),
        _dei(slot, "2026-07-20"),
    )
    assert w.evaluate_cell(revenue, {}, probe, slot) == {"status": "absent", "reason_code": "absent_ifrs_taxonomy"}
    assert w.companyfacts_missing_accession(probe, own) is False

    dei_only = _facts(_dei(slot, "2026-07-20"))
    assert w.companyfacts_missing_accession(dei_only, own) is False
    assert w.evaluate_cell(revenue, {}, dei_only, slot) == {"status": "absent", "reason_code": "absent_no_alias_fact"}

    nowhere = _facts(("ifrs-full", "Revenue", "USD", [_fact(_accn(1, 50), "2026-06-30", start="2025-07-02")]))
    assert w.companyfacts_missing_accession(nowhere, own) is True
    assert w.evaluate_cell(revenue, {}, nowhere, slot) == {
        "status": "stale", "reason_code": "companyfacts_missing_accession"}


# W-R2 m6: slot dates must be ISO calendar dates ------------------------------------------------------------


def test_invalid_slot_dates_are_typed_failures():
    direct = _spec("total_assets", aliases=[(10, "us-gaap", "Assets")])
    formula = _spec("ratio", deps=("total_assets",))
    specs = {"total_assets": direct, "ratio": formula}
    for overrides in ({"report_date": "6/30/2026"}, {"filing_date": "20260814"}, {"filing_date": ""}):
        slot = _slot(**overrides)
        facts = _facts(("us-gaap", "Assets", "USD", [_fact(slot["accession"], slot["report_date"])]))
        for spec in (direct, formula):
            counters: dict = {}
            assert w.evaluate_cell(spec, specs, facts, slot, counters) == {
                "status": "failed_extraction", "reason_code": "invalid_slot_date"}
            assert counters == {"invalid_slot_date": 1}
    assert w.evaluate_cell(direct, specs, _facts(("us-gaap", "Assets", "USD", [_fact(_slot()["accession"],
                                                                                  "2026-06-30")])), _slot())[
        "status"] == "present"


# W-R2 m7: the cover-date policy is rule-clocked --------------------------------------------------------------


def test_cover_date_policy_is_rule_clocked():
    assert w.COVER_DATE_POLICY["available_at"] == "2026-10-19T00:00:00Z"
    slot = _slot()
    facts = _facts(_own_usgaap_marker(slot), _dei(slot, "2026-07-20"))
    spec = _shares_spec()

    counters: dict = {}
    cell = w.evaluate_cell(spec, {}, facts, slot, counters, recorded_at="2026-10-18T23:59:59Z")
    assert cell == {"status": "absent", "reason_code": "absent_period_mismatch"}
    assert counters == {"cover_fallback_policy_not_visible": 1}

    cell = w.evaluate_cell(spec, {}, facts, slot, recorded_at="2026-10-19T00:00:00Z")
    assert cell["qualifier"] == "cover_date_as_of" and cell["as_of"] == "2026-07-20"

    counters = {}
    assert w.evaluate_cell(spec, {}, facts, slot, counters) == {
        "status": "absent", "reason_code": "absent_period_mismatch"}
    assert counters == {"cover_fallback_policy_not_visible": 1}

    with pytest.raises(ValueError):
        w.evaluate_cell(spec, {}, facts, slot, recorded_at="2026-10-19T00:00:00")

    _base, slots, loader, specs, provenance = _rewrite_fixture()
    _manifest, counts = w.rewrite_manifest(_base, slots, loader, specs, "2026-10-18T00:00:00Z", provenance)
    assert counts["present_qualified"] == {"all": 0, "core": 0}
    assert counts["cover_fallback_policy_not_visible"] == 1


# W-R2 NIT: exact form membership ---------------------------------------------------------------------------


def test_cover_date_forms_match_exactly():
    spec = _shares_spec()
    for form in ("10-K/A", "10-KT", "10-QT", "10-K405"):
        slot = _slot(form=form)
        counters: dict = {}
        cell = w.evaluate_cell(spec, {}, _facts(_own_usgaap_marker(slot), _dei(slot, "2026-07-20")), slot, counters,
                               recorded_at=RULE_CLOCK)
        assert "qualifier" not in cell
        assert counters == {"cover_fallback_form_not_covered": 1}
    for form in ("10-K", "10-Q"):
        slot = _slot(form=form)
        cell = w.evaluate_cell(spec, {}, _facts(_own_usgaap_marker(slot), _dei(slot, "2026-07-20")), slot,
                               recorded_at=RULE_CLOCK)
        assert cell["qualifier"] == "cover_date_as_of"


# W-R2 m8: the CLI runs with sockets refused before the writer is imported -------------------------------------

_GUARDED_CLI = """
import socket, sys
def refuse(*_args, **_kwargs):
    raise AssertionError("network access attempted")
socket.socket = refuse
socket.create_connection = refuse
socket.getaddrinfo = refuse
from scripts import fif_coverage_writer as w
raise SystemExit(w.main(sys.argv[1:]))
"""


def test_cli_runs_offline_with_socket_guard_installed_before_import(tmp_path, capsys):
    base, slots, loader, _specs, _provenance = _rewrite_fixture()
    cache = tmp_path / "cache"
    cache.mkdir()
    for cik in {slot["cik"] for slot in slots}:
        facts = loader(cik)
        if facts is not None:
            payload = json.dumps({"facts": facts}).encode("utf-8")
            (cache / f"{w.companyfacts_cache_key(cik)}.gz").write_bytes(gzip.compress(payload, mtime=0))
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps(base), encoding="utf-8")
    slots_path = tmp_path / "slots.csv"
    header = list(slots[0])
    slots_path.write_text(
        ",".join(header) + "\n" + "".join(",".join(slot[k] for k in header) + "\n" for slot in slots),
        encoding="utf-8",
    )

    def args(out):
        return ["rewrite", "--base-manifest", str(base_path), "--slots", str(slots_path), "--facts-cache",
                str(cache), "--recorded-at", RULE_CLOCK, "--out", str(out), "--repo-root", str(ROOT)]

    guarded = tmp_path / "guarded.json"
    result = subprocess.run(
        [sys.executable, "-c", _GUARDED_CLI, *args(guarded)],
        cwd=str(ROOT), capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert result.returncode == 0, result.stderr
    in_process = tmp_path / "in_process.json"
    assert w.main(args(in_process)) == 0
    capsys.readouterr()
    assert guarded.read_bytes() == in_process.read_bytes()


# --- A36: the not-presented (NP) branch behind --np-linkbases -----------------
#
# Synthetic linkbases only (the builders tests/test_fundamental_forensics_not_presented.py
# already uses for the governed pack), synthetic issuers, and the real governed
# not-presented pack: no issuer bytes, no ticker/CIK literal.

import hashlib  # noqa: E402
import importlib.util  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from engine.fundamental_forensics.coverage_manifest import map_metric_cell  # noqa: E402
from engine.fundamental_forensics.not_presented import (  # noqa: E402
    NotPresentedEvidence,
    load_not_presented_pack,
)
from engine.fundamental_forensics.query import CellState  # noqa: E402
from tests.test_fundamental_forensics_not_presented import calc_xml, pre_xml  # noqa: E402

NP_CLOCK = "2026-10-22T00:00:00Z"
NP_BEFORE_CLOCK = "2026-10-20T23:59:59Z"  # before the pack's available_at
NP_PARENT_ROLE = "http://ext.example/role/ConsolidatedBalanceSheets"
PARENT_COMMIT = "9eaefeeddd9fb22109c23ea3e5f966669c8fded8"

_NP_LC_ARCS = [
    ("us-gaap:LiabilitiesCurrent", "us-gaap:AccountsPayableCurrent", "1"),
    ("us-gaap:LiabilitiesCurrent", "us-gaap:LiabilitiesOtherCurrent", "1"),
]
_NP_LNC_ARCS = [
    ("us-gaap:LiabilitiesNoncurrent", "us-gaap:DeferredIncomeTaxLiabilitiesNoncurrent", "1"),
    ("us-gaap:LiabilitiesNoncurrent", "us-gaap:LiabilitiesNoncurrentOther", "1"),
]
_NP_CAL = calc_xml([(NP_PARENT_ROLE, _NP_LC_ARCS), (NP_PARENT_ROLE, _NP_LNC_ARCS)])
_NP_PRE = pre_xml([(
    NP_PARENT_ROLE,
    [
        "us-gaap:LiabilitiesCurrent",
        "us-gaap:AccountsPayableCurrent",
        "us-gaap:LiabilitiesOtherCurrent",
        "us-gaap:LiabilitiesNoncurrent",
        "us-gaap:DeferredIncomeTaxLiabilitiesNoncurrent",
        "us-gaap:LiabilitiesNoncurrentOther",
    ],
)])


def _bs_facts(slot, *, lnc=True, liab_current=100000, extra=()):
    """A balance sheet whose current/noncurrent parents decompose exactly."""
    accn, report = slot["accession"], slot["report_date"]
    entries = [
        ("us-gaap", "LiabilitiesCurrent", "USD", [_fact(accn, report, val=liab_current)]),
        ("us-gaap", "AccountsPayableCurrent", "USD", [_fact(accn, report, val=40000)]),
        ("us-gaap", "LiabilitiesOtherCurrent", "USD", [_fact(accn, report, val=60000)]),
    ]
    if lnc:
        entries += [
            ("us-gaap", "LiabilitiesNoncurrent", "USD", [_fact(accn, report, val=200000)]),
            ("us-gaap", "DeferredIncomeTaxLiabilitiesNoncurrent", "USD", [_fact(accn, report, val=50000)]),
            ("us-gaap", "LiabilitiesNoncurrentOther", "USD", [_fact(accn, report, val=150000)]),
        ]
    return _facts(*entries, *extra)


def _np_metric(metric_id, alias, kind="instant"):
    return _spec(metric_id, kind=kind, aliases=[(10, "us-gaap", alias)])


_ST_DEBT = _np_metric("short_term_debt", "SyntheticShortTermDebtLine")
_LTD_CURRENT = _np_metric("long_term_debt_current", "SyntheticLongTermDebtCurrentLine")
_LTD = _np_metric("long_term_debt", "SeniorNotesNoncurrent")
_CASH = _np_metric("cash_and_cash_equivalents", "CashAndCashEquivalentsAtCarryingValue")

_TOTAL_DEBT_POLICY = {
    "mode": "qualified_sum",
    "qualified_operand": "withhold",
    "eligible_operands": ("short_term_debt", "long_term_debt_current", "long_term_debt"),
    "all_not_presented": "not_applicable",
}
_INHERIT_POLICY = {
    "mode": "not_applicable",
    "qualified_operand": "inherit",
    "eligible_operands": (),
    "all_not_presented": None,
}


def _formula_spec(metric_id, deps, policy):
    spec = _spec(metric_id, deps=deps)
    spec["np_formula_policy"] = policy
    return spec


def _np_dir(tmp_path, entries, *, schema=None, mutate=None):
    """One fif.np_linkbases/v1 directory; entries map accession -> (cal, pre) or None."""
    root = Path(tmp_path) / "np"
    root.mkdir(parents=True)
    index_entries = {}
    for accn, payload in entries.items():
        if payload is None:
            index_entries[accn] = {"status": "capture_failed"}
            continue
        cal, pre = payload
        cal_rel, pre_rel = f"{accn}_cal.xml.gz", f"{accn}_pre.xml.gz"
        (root / cal_rel).write_bytes(gzip.compress(cal, mtime=0))
        (root / pre_rel).write_bytes(gzip.compress(pre, mtime=0))
        index_entries[accn] = {
            "cik": accn.split("-", 1)[0],
            "cal": cal_rel,
            "pre": pre_rel,
            "cal_sha256": hashlib.sha256(cal).hexdigest(),
            "pre_sha256": hashlib.sha256(pre).hexdigest(),
            "cal_name": f"{accn}_cal.xml",
            "pre_name": f"{accn}_pre.xml",
            "status": "ok",
        }
    if mutate is not None:
        mutate(index_entries)
    (root / "index.json").write_text(
        json.dumps({
            "schema": schema or w.NP_LINKBASES_SCHEMA,
            "captured_at": "2026-11-01T00:00:00Z",
            "user_agent": "synthetic-agent",
            "entries": index_entries,
        }),
        encoding="utf-8",
    )
    return root


def _np_ctx(tmp_path, entries, recorded_at=NP_CLOCK):
    return w.NPContext(
        pack=load_not_presented_pack(),
        linkbases=w.load_np_linkbases(_np_dir(tmp_path, entries)),
        recorded_at=w._utc_instant(recorded_at),
    )


# T1: byte identity without the flag -------------------------------------------------


# CI checks out without history, so PARENT_COMMIT may be unreachable. The parent
# writer's dump for _rewrite_fixture() and its count keys are pinned here (recorded
# by running the PARENT_COMMIT writer on this fixture) and asserted on every run; the
# live comparison against the parent module runs too whenever git can reach it.
PARENT_T1_DUMP_SHA256 = "93a8aa6a5bc393672f5a6e32e39438daa47ba08e1fd32d03f28992a7b5a2b1b5"
PARENT_T1_COUNT_KEYS = frozenset({
    "by_reason",
    "cells_rewritten",
    "cover_date_multi_class",
    "cover_fallback_alias_not_visible",
    "cover_fallback_form_not_covered",
    "cover_fallback_policy_not_visible",
    "cover_multi_value",
    "cover_window_ambiguous",
    "facts_unavailable_issuers",
    "formula_blocked_by_qualified_operand",
    "invalid_slot_date",
    "issuer_rollups",
    "metric_not_visible",
    "present_qualified",
    "present_strict",
    "slot_accession_mismatch",
    "slot_row_missing",
})


def _parent_module(tmp_path):
    """The PARENT_COMMIT writer, or None when git cannot reach that commit."""
    shown = subprocess.run(
        ["git", "-c", "gc.auto=0", "show", f"{PARENT_COMMIT}:scripts/fif_coverage_writer.py"],
        cwd=str(ROOT), capture_output=True,
    )
    if shown.returncode != 0:
        return None
    source = shown.stdout
    path = tmp_path / "parent_fif_coverage_writer.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("parent_fif_coverage_writer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_t1_without_the_flag_the_output_is_byte_identical_to_the_parent_writer(tmp_path):
    base, slots, loader, specs, provenance = _rewrite_fixture()
    mine_manifest, mine_counts = w.rewrite_manifest(
        copy.deepcopy(base), slots, loader, copy.deepcopy(specs), RULE_CLOCK, copy.deepcopy(provenance),
        np_context=None,
    )
    mine_dump = w.dump_manifest(mine_manifest)
    assert hashlib.sha256(mine_dump).hexdigest() == PARENT_T1_DUMP_SHA256
    assert set(mine_counts) == PARENT_T1_COUNT_KEYS
    assert w.NP_COUNTERS_KEY not in mine_counts

    parent = _parent_module(tmp_path)
    if parent is not None:
        base, slots, loader, specs, provenance = _rewrite_fixture()
        parent_manifest, parent_counts = parent.rewrite_manifest(
            copy.deepcopy(base), slots, loader, copy.deepcopy(specs), RULE_CLOCK, copy.deepcopy(provenance)
        )
        assert mine_dump == parent.dump_manifest(parent_manifest)
        assert set(parent_counts) == PARENT_T1_COUNT_KEYS


# T2: a strict metric with governed NP evidence ---------------------------------------


def test_t2_strict_metric_with_np_evidence_becomes_not_applicable(tmp_path):
    slot = _slot()
    specs = {"short_term_debt": _ST_DEBT}
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    counters: dict = {}
    cell = w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, counters,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell["status"] == "not_applicable"
    assert (cell["reason_code"], cell["kernel_reason"]) == ("not_presented", "not_presented")
    assert cell["na_basis"] == "not_presented_item"
    assert cell["np_rule_id"] == "not_presented.short_term_debt/v1"
    assert cell["np_accession"] == slot["accession"]
    assert cell["np_cal_sha256"] == hashlib.sha256(_NP_CAL).hexdigest()
    assert cell["np_pre_sha256"] == hashlib.sha256(_NP_PRE).hexdigest()
    assert cell["np_footing"] == "exact"
    assert cell["np_parent_concepts"] == ["us-gaap:LiabilitiesCurrent"]
    assert set(cell) == {
        "status", "reason_code", "kernel_reason", "na_basis",
        "np_kind", "np_rule_id", "np_rule_version", "np_rules_sha256",
        "np_parent_concepts", "np_roles_checked", "np_children_n",
        "np_children_with_fact_n", "np_footing", "np_cal_sha256", "np_pre_sha256",
        "np_accession",
    }
    assert counters == {}
    assert ctx.counters.get("np_outcome:not_presented") == 1

    # The same cell equals what the served mapping emits for the served verdict.
    evidence = NotPresentedEvidence.from_dict({key: cell[key] for key in (
        "np_kind", "np_rule_id", "np_rule_version", "np_rules_sha256", "np_parent_concepts",
        "np_roles_checked", "np_children_n", "np_children_with_fact_n", "np_footing",
        "np_cal_sha256", "np_pre_sha256", "np_accession")})
    served = map_metric_cell(
        SimpleNamespace(
            metric_id="short_term_debt",
            state=CellState.NOT_APPLICABLE,
            reason="not_presented",
            provenance=SimpleNamespace(
                na_basis="not_presented_item", not_presented=evidence, reason=None
            ),
        ),
        cik=slot["cik"], period_id=slot["slot_id"], source_generation_id="synthetic",
        np_pack=ctx.pack,
    )
    assert {key: value for key, value in served.items() if key in cell} == cell
    assert set(cell) <= set(served)

    # Without the flag the same inputs keep the plain absent cell.
    plain = w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, {}, recorded_at=NP_CLOCK)
    assert plain == {"status": "absent", "reason_code": "absent_no_alias_fact"}


# T3: the item presented, or footing off, keeps the absent cell ------------------------


def test_t3_presented_or_unbalanced_linkbase_keeps_absent_with_outcome_counter(tmp_path):
    slot = _slot()
    specs = {"short_term_debt": _ST_DEBT}
    presented_pre = pre_xml([(
        NP_PARENT_ROLE,
        ["us-gaap:LiabilitiesCurrent", "us-gaap:AccountsPayableCurrent",
         "us-gaap:LiabilitiesOtherCurrent", "us-gaap:CommercialPaper"],
    )])
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, presented_pre)})
    cell = w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, recorded_at=NP_CLOCK,
                           np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert ctx.counters.get("np_outcome:np_family_in_statement_pre") == 1

    off = _np_ctx(tmp_path / "off", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot, liab_current=100001), slot,
                           recorded_at=NP_CLOCK, np_context=off)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert off.counters.get("np_outcome:np_unbalanced") == 1


# T4: every fail-closed case keeps the absent result -----------------------------------


def test_t4_fail_closed_cases_keep_the_absent_result(tmp_path):
    slot = _slot()
    specs = {"short_term_debt": _ST_DEBT, "cash_dividends_paid": _np_metric(
        "cash_dividends_paid", "SyntheticDividendsLine", kind="duration")}
    absent = {"status": "absent", "reason_code": "absent_no_alias_fact"}

    amended = _slot(amendments=_accn(1, 2))
    ctx = _np_ctx(tmp_path / "amended", {amended["accession"]: (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(_ST_DEBT, specs, _bs_facts(amended), amended, np_context=ctx) == absent
    assert ctx.counters.get("np_skipped_amended_slot") == 1

    other = _accn(1, 99)
    foreign_parent = _facts(
        ("us-gaap", "MarkerConcept", "USD", [_fact(slot["accession"], slot["report_date"])]),
        ("us-gaap", "LiabilitiesCurrent", "USD", [_fact(other, slot["report_date"], val=100000)]),
    )
    ctx = _np_ctx(tmp_path / "foreign", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(_ST_DEBT, specs, foreign_parent, slot, np_context=ctx) == absent
    assert ctx.counters.get("np_outcome:np_no_parent") == 1

    interim = _slot(slot_id="I1", n=3, report_date="2026-06-30", filing_date="2026-08-01",
                    form="10-Q")
    two_quarters = _facts(
        ("us-gaap", "FinancingMarker", "USD", [_fact(interim["accession"], interim["report_date"])]),
        ("us-gaap", "NetCashProvidedByUsedInFinancingActivities", "USD", [
            _fact(interim["accession"], "2026-06-30", val=5, start="2026-04-06"),
            _fact(interim["accession"], "2026-06-30", val=5, start="2026-04-01"),
        ]),
    )
    ctx = _np_ctx(tmp_path / "mixed", {interim["accession"]: (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(specs["cash_dividends_paid"], specs, two_quarters, interim,
                           np_context=ctx) == absent
    assert ctx.counters.get("np_mixed_duration") == 1

    conflicting = _bs_facts(slot, extra=[
        ("us-gaap", "LiabilitiesCurrent", "USD", [_fact(slot["accession"], slot["report_date"], val=99999)]),
    ])
    ctx = _np_ctx(tmp_path / "conflict", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(_ST_DEBT, specs, conflicting, slot, np_context=ctx) == absent
    assert ctx.counters.get("np_conflicting_value") == 1

    sha_bad = _np_dir(tmp_path / "sha", {slot["accession"]: (_NP_CAL, _NP_PRE)},
                      mutate=lambda entries: entries[slot["accession"]].update(
                          cal_sha256="0" * 64))
    ctx = w.NPContext(pack=load_not_presented_pack(), linkbases=w.load_np_linkbases(sha_bad),
                      recorded_at=w._utc_instant(NP_CLOCK))
    assert w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, np_context=ctx) == absent
    assert ctx.counters.get("np_linkbase_sha_mismatch") == 1

    ctx = _np_ctx(tmp_path / "missing", {_accn(1, 55): (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, np_context=ctx) == absent
    assert ctx.counters.get("np_no_linkbase_entry") == 1

    ctx = _np_ctx(tmp_path / "noclock", {slot["accession"]: (_NP_CAL, _NP_PRE)},
                  recorded_at=NP_BEFORE_CLOCK)
    assert w.evaluate_cell(_ST_DEBT, specs, _bs_facts(slot), slot, recorded_at=NP_BEFORE_CLOCK,
                           np_context=ctx) == absent
    assert ctx.counters.get("np_outcome:np_no_rule") == 1


# T5: NP never touches a present, stale, period-mismatched or cover-date cell ------------


def test_t5_np_never_touches_non_absent_cells(tmp_path):
    slot = _slot()
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    assets = _np_metric("total_assets", "Assets")
    specs = {SHARES: _shares_spec(), "total_assets": assets}

    present = _bs_facts(slot, extra=[
        ("us-gaap", "Assets", "USD", [_fact(slot["accession"], slot["report_date"])]),
    ])
    assert w.evaluate_cell(assets, specs, present, slot, np_context=ctx) == {
        "status": "present", "reason_code": "present"}

    mismatch = _bs_facts(slot, extra=[
        ("us-gaap", "Assets", "USD", [_fact(slot["accession"], "2025-12-31")]),
    ])
    assert w.evaluate_cell(assets, specs, mismatch, slot, np_context=ctx) == {
        "status": "absent", "reason_code": "absent_period_mismatch"}

    stale = _facts(("us-gaap", "Assets", "USD", [_fact(_accn(1, 88), "2026-06-30")]))
    assert w.evaluate_cell(assets, specs, stale, slot, np_context=ctx) == {
        "status": "stale", "reason_code": "companyfacts_missing_accession"}

    cover = _bs_facts(slot, extra=[
        ("dei", DEI_SHARES[1], "shares", [_fact(slot["accession"], "2026-07-20")]),
    ])
    cell = w.evaluate_cell(specs[SHARES], specs, cover, slot, recorded_at=NP_CLOCK, np_context=ctx)
    assert cell["qualifier"] == "cover_date_as_of" and cell["as_of"] == "2026-07-20"

    assert ctx.counters == {}


# T6: the served formula not-presented policy on the writer's operands ------------------


def test_t6_formula_np_policy_mirrors_the_served_decisions(tmp_path):
    slot = _slot()
    cash_entry = ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "USD",
                  [_fact(slot["accession"], slot["report_date"], val=250000)])
    senior_entry = ("us-gaap", "SeniorNotesNoncurrent", "USD",
                    [_fact(slot["accession"], slot["report_date"], val=700000)])
    specs = {
        "short_term_debt": _ST_DEBT,
        "long_term_debt_current": _LTD_CURRENT,
        "long_term_debt": _LTD,
        "cash_and_cash_equivalents": _CASH,
        "total_debt": _formula_spec(
            "total_debt",
            ("short_term_debt", "long_term_debt_current", "long_term_debt"),
            _TOTAL_DEBT_POLICY,
        ),
        "net_debt": _formula_spec(
            "net_debt", ("total_debt", "cash_and_cash_equivalents"), _INHERIT_POLICY
        ),
        "cash_to_total_debt": _formula_spec(
            "cash_to_total_debt", ("cash_and_cash_equivalents", "total_debt"), _INHERIT_POLICY
        ),
        "plain_sum": _spec("plain_sum", deps=("short_term_debt", "cash_and_cash_equivalents")),
        "ratio_withhold": _formula_spec(
            "ratio_withhold", ("total_debt",),
            {"mode": "not_applicable", "qualified_operand": "withhold",
             "eligible_operands": (), "all_not_presented": None},
        ),
    }
    pack_ref = f"{load_not_presented_pack().pack_id}/{load_not_presented_pack().pack_version}"

    # All debt operands NP -> total_debt is the served formula N/A cell; the
    # dependents read it as an NP operand and follow their inherit policy.
    all_np = _bs_facts(slot, extra=[cash_entry])
    ctx = _np_ctx(tmp_path / "allnp", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(specs["total_debt"], specs, all_np, slot, np_context=ctx)
    assert cell == {
        "status": "not_applicable",
        "reason_code": "formula_not_presented",
        "kernel_reason": (
            "formula_not_presented: short_term_debt, long_term_debt_current, long_term_debt"
        ),
        "na_basis": "kernel",
    }
    for metric_id in ("net_debt", "cash_to_total_debt"):
        cell = w.evaluate_cell(specs[metric_id], specs, all_np, slot, np_context=ctx)
        assert cell == {
            "status": "not_applicable",
            "reason_code": "formula_not_presented",
            "kernel_reason": "formula_not_presented: total_debt",
            "na_basis": "kernel",
        }
    assert ctx.counters.get("np_formula_outcome:not_applicable") == 5

    # No policy -> withhold: the served withheld absent cell.
    cell = w.evaluate_cell(specs["plain_sum"], specs, all_np, slot, np_context=ctx)
    assert cell == {
        "status": "absent",
        "reason_code": "not_presented_dependency",
        "kernel_reason": "not_presented_dependency: short_term_debt",
    }

    # Some operands PRESENT, the rest NP -> present with the served qualifier.
    qualified = _bs_facts(slot, extra=[cash_entry, senior_entry])
    ctx = _np_ctx(tmp_path / "qualified", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(specs["total_debt"], specs, qualified, slot, np_context=ctx)
    assert cell == {
        "status": "present",
        "reason_code": "present",
        "qualifier": "qualified_not_presented: long_term_debt_current, short_term_debt",
        "qualifier_policy": pack_ref,
    }
    # net_debt / cash_to_total_debt inherit the qualifier exactly as served.
    for metric_id in ("net_debt", "cash_to_total_debt"):
        cell = w.evaluate_cell(specs[metric_id], specs, qualified, slot, np_context=ctx)
        assert cell["status"] == "present" and cell["reason_code"] == "present"
        assert cell["qualifier"] == "qualified_not_presented: long_term_debt_current, short_term_debt"
        assert cell["qualifier_policy"] == pack_ref
    # A withhold dependent stays absent with the served qualified reason.
    cell = w.evaluate_cell(specs["ratio_withhold"], specs, qualified, slot, np_context=ctx)
    assert cell == {
        "status": "absent",
        "reason_code": "qualified_dependency",
        "kernel_reason": "qualified_dependency: total_debt",
    }

    # An OTHER operand (long_term_debt has no parent fact -> np_no_parent)
    # keeps the existing formula result unchanged.
    other = _bs_facts(slot, lnc=False, extra=[cash_entry])
    ctx = _np_ctx(tmp_path / "other", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    assert w.evaluate_cell(specs["total_debt"], specs, other, slot, np_context=ctx) == {
        "status": "absent", "reason_code": "absent_dependency"}
    assert ctx.counters.get("np_outcome:np_no_parent") >= 1


# T7: rollups and counts -----------------------------------------------------------------


def test_t7_qualified_np_cells_count_qualified_and_na_does_not_fail_the_window(tmp_path):
    annual = _slot(1)
    interim = _slot(1, slot_id="I1", n=3, report_date="2026-03-31", filing_date="2026-05-08",
                    form="10-Q")
    specs = {
        "short_term_debt": _ST_DEBT,
        "long_term_debt_current": _LTD_CURRENT,
        "long_term_debt": _LTD,
        "total_debt": _formula_spec(
            "total_debt",
            ("short_term_debt", "long_term_debt_current", "long_term_debt"),
            _TOTAL_DEBT_POLICY,
        ),
    }

    def cell(slot_row, metric_id):
        return {"cik": slot_row["cik"], "period_id": slot_row["slot_id"],
                "field_id": f"metric:{metric_id}", "accession": slot_row["accession"],
                "tier": "core", "status": "absent", "reason_code": "absent_no_alias_fact"}

    base = {
        "cells": [cell(s, metric_id) for s in (annual, interim) for metric_id in sorted(specs)],
        "issuers": [{"cik": annual["cik"], "tier_assigned": "core"}],
    }
    facts = _bs_facts(annual, extra=[
        ("us-gaap", "SeniorNotesNoncurrent", "USD", [_fact(annual["accession"], annual["report_date"], val=700000)]),
    ])
    for taxonomy, concepts in _bs_facts(interim, extra=[
        ("us-gaap", "SeniorNotesNoncurrent", "USD", [_fact(interim["accession"], interim["report_date"], val=650000)]),
    ]).items():
        for concept, entry in concepts.items():
            units = facts.setdefault(taxonomy, {}).setdefault(concept, {}).setdefault("units", {})
            for unit, fact_list in entry["units"].items():
                units.setdefault(unit, []).extend(fact_list)
    ctx = _np_ctx(tmp_path, {annual["accession"]: (_NP_CAL, _NP_PRE),
                             interim["accession"]: (_NP_CAL, _NP_PRE)})
    manifest, counts = w.rewrite_manifest(base, [annual, interim], {annual["cik"]: facts}.get,
                                          specs, NP_CLOCK, {}, np_context=ctx)

    by_key = {(c["period_id"], c["field_id"]): c for c in manifest["cells"]}
    for period in ("A1", "I1"):
        assert by_key[(period, "metric:short_term_debt")]["status"] == "not_applicable"
        assert by_key[(period, "metric:long_term_debt_current")]["status"] == "not_applicable"
        assert by_key[(period, "metric:long_term_debt")]["status"] == "present"
        total = by_key[(period, "metric:total_debt")]
        assert total["status"] == "present"
        assert w._is_labelled(total) is True
        assert w._strict_status(total) == "present_labelled"

    (issuer,) = manifest["issuers"]
    assert issuer["core_pass"] is True
    assert issuer["core_pass_strict"] is False
    assert (issuer["present_cells"], issuer["absent_cells"], issuer["na_cells"]) == (4, 0, 4)
    assert issuer["present_cells_strict"] == 2
    assert counts["present_strict"] == {"all": 2, "core": 2}
    assert counts["present_qualified"] == {"all": 2, "core": 2}
    np_counts = counts[w.NP_COUNTERS_KEY]
    assert np_counts["np_outcome:not_presented"] == 8
    assert np_counts["np_formula_outcome:present"] == 2


# T8: a malformed index refuses the run ----------------------------------------------------


def _cli_args(tmp_path):
    base, slots, loader, _specs, _provenance = _rewrite_fixture()
    cache = tmp_path / "cache"
    cache.mkdir()
    for cik in {slot["cik"] for slot in slots}:
        facts = loader(cik)
        if facts is not None:
            payload = json.dumps({"facts": facts}).encode("utf-8")
            (cache / f"{w.companyfacts_cache_key(cik)}.gz").write_bytes(gzip.compress(payload, mtime=0))
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps(base), encoding="utf-8")
    slots_path = tmp_path / "slots.csv"
    header = list(slots[0])
    slots_path.write_text(
        ",".join(header) + "\n" + "".join(",".join(slot[k] for k in header) + "\n" for slot in slots),
        encoding="utf-8",
    )
    return ["rewrite", "--base-manifest", str(base_path), "--slots", str(slots_path),
            "--facts-cache", str(cache), "--recorded-at", RULE_CLOCK,
            "--repo-root", str(ROOT)]


def test_t8_index_schema_mismatch_and_path_escape_exit_nonzero(tmp_path, capsys):
    plain = _cli_args(tmp_path)
    out = tmp_path / "out.json"
    accn = _accn(1, 1)

    bad_schema = _np_dir(tmp_path / "schema", {accn: (_NP_CAL, _NP_PRE)},
                         schema="fif.np_linkbases/v2")
    assert w.main([*plain, "--np-linkbases", str(bad_schema), "--out", str(out)]) == 2
    assert "schema" in capsys.readouterr().err
    assert not out.exists()

    escaping = _np_dir(tmp_path / "escape", {accn: (_NP_CAL, _NP_PRE)},
                       mutate=lambda entries: entries[accn].update(cal="../outside.xml.gz"))
    assert w.main([*plain, "--np-linkbases", str(escaping), "--out", str(out)]) == 2
    assert "inside the directory" in capsys.readouterr().err
    assert not out.exists()

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; from scripts import fif_coverage_writer as w;"
         "raise SystemExit(w.main(sys.argv[1:]))",
         *plain, "--np-linkbases", str(bad_schema), "--out", str(out)],
        cwd=str(ROOT), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert result.returncode != 0
    assert "schema" in result.stderr


def _np_ctx_governed(tmp_path, entries, governed, recorded_at=NP_CLOCK):
    """An NPContext whose governed alias set is the synthetic registry view."""
    return w.NPContext(
        pack=load_not_presented_pack(),
        linkbases=w.load_np_linkbases(_np_dir(tmp_path, entries)),
        recorded_at=w._utc_instant(recorded_at),
        governed_qnames=frozenset(governed),
    )


# T9 (defect 1): an alias fact from another accession at the report date -----


def test_t9_other_accession_alias_fact_keeps_the_absent_result(tmp_path):
    slot = _slot()
    other = _accn(1, 42)
    leaked_alias = ("us-gaap", "SyntheticShortTermDebtLine", "USD",
                    [_fact(other, slot["report_date"], val=5000)])
    absent = {"status": "absent", "reason_code": "absent_no_alias_fact"}

    # The reviewer's shape: the linkbases say not presented, but another
    # accession carries a USD alias fact at end == report_date.
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT},
                           _bs_facts(slot, extra=[leaked_alias]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == absent
    assert ctx.counters.get("np_alias_fact_other_accession") == 1

    # Without the other-accession fact the same inputs are the T2 not-presented
    # verdict, so it is the leak that keeps the absent cell.
    clean = _np_ctx(tmp_path / "clean", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT}, _bs_facts(slot), slot,
                           recorded_at=NP_CLOCK, np_context=clean)
    assert cell["status"] == "not_applicable"
    assert clean.counters.get("np_alias_fact_other_accession") is None

    # The same metric as a formula operand: the operand is OTHER, so the
    # formula keeps its existing absent_dependency result.
    cash_entry = ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "USD",
                  [_fact(slot["accession"], slot["report_date"], val=250000)])
    specs = {
        "short_term_debt": _ST_DEBT,
        "long_term_debt_current": _LTD_CURRENT,
        "long_term_debt": _LTD,
        "total_debt": _formula_spec(
            "total_debt",
            ("short_term_debt", "long_term_debt_current", "long_term_debt"),
            _TOTAL_DEBT_POLICY,
        ),
    }
    ctx = _np_ctx(tmp_path / "formula", {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(specs["total_debt"], specs,
                           _bs_facts(slot, extra=[cash_entry, leaked_alias]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_dependency"}
    assert ctx.counters.get("np_alias_fact_other_accession") == 1


# T10 (defect 2): a competing governed span changes the census's request ------


def test_t10_competing_governed_span_keeps_the_absent_result(tmp_path):
    # The reviewer's run-proven shape: universe {378d@OTHER, 371d@anchor}.
    # 371 inclusive days = 53 fiscal weeks (the anchor's own in-class span);
    # 378 inclusive days is the longer governed span the census requests.
    annual = _slot()
    other = _accn(1, 7)
    own_span = ("2025-06-25", "2026-06-30")
    longer_span = ("2025-06-18", "2026-06-30")
    governed = {"us-gaap:Revenues", "us-gaap:OperatingIncomeLoss"}
    dividends = _np_metric("cash_dividends_paid", "SyntheticDividendsLine", kind="duration")
    absent = {"status": "absent", "reason_code": "absent_no_alias_fact"}

    facts = _bs_facts(annual, extra=[
        ("us-gaap", "OperatingIncomeLoss", "USD",
         [_fact(annual["accession"], "2026-06-30", val=9, start=own_span[0])]),
        ("us-gaap", "Revenues", "USD",
         [_fact(other, "2026-06-30", val=11, start=longer_span[0])]),
    ])
    # duration_for_slot (annual: the longest span ending at the report date)
    # requests the other filing's 378-day span, not the anchor's 371-day one.
    assert w._np_requested_span(facts, annual, frozenset(governed)) == longer_span
    ctx = _np_ctx_governed(tmp_path, {annual["accession"]: (_NP_CAL, _NP_PRE)}, governed)
    cell = w.evaluate_cell(dividends, {"cash_dividends_paid": dividends}, facts, annual,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == absent
    assert ctx.counters.get("np_span_not_requested") == 1

    # Without the competing span the census requests the anchor's own span and
    # the NP evaluation proceeds to a verdict.
    alone = _bs_facts(annual, extra=[
        ("us-gaap", "OperatingIncomeLoss", "USD",
         [_fact(annual["accession"], "2026-06-30", val=9, start=own_span[0])]),
    ])
    assert w._np_requested_span(alone, annual, frozenset(governed)) == own_span
    ctx = _np_ctx_governed(tmp_path / "alone", {annual["accession"]: (_NP_CAL, _NP_PRE)},
                           governed)
    w.evaluate_cell(dividends, {"cash_dividends_paid": dividends}, alone, annual,
                    recorded_at=NP_CLOCK, np_context=ctx)
    assert ctx.counters.get("np_span_not_requested") is None
    assert any(str(key).startswith("np_outcome:") for key in ctx.counters)

    # The interim analogue: duration_for_slot takes the SHORTEST span ending at
    # the report date, so a shorter competing span (80 days vs the anchor's own
    # 91-day quarter) is the one that changes the request.
    interim = _slot(slot_id="I1", n=4, report_date="2026-06-30", filing_date="2026-08-01",
                    form="10-Q")
    own_quarter = ("2026-04-01", "2026-06-30")
    shorter_span = ("2026-04-12", "2026-06-30")
    facts_i = _bs_facts(interim, extra=[
        ("us-gaap", "OperatingIncomeLoss", "USD",
         [_fact(interim["accession"], "2026-06-30", val=9, start=own_quarter[0])]),
        ("us-gaap", "Revenues", "USD",
         [_fact(other, "2026-06-30", val=11, start=shorter_span[0])]),
    ])
    assert w._np_requested_span(facts_i, interim, frozenset(governed)) == shorter_span
    ctx = _np_ctx_governed(tmp_path / "interim", {interim["accession"]: (_NP_CAL, _NP_PRE)},
                           governed)
    cell = w.evaluate_cell(dividends, {"cash_dividends_paid": dividends}, facts_i, interim,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == absent
    assert ctx.counters.get("np_span_not_requested") == 1


# T11 (regression): the single-accession, single-span verdicts survive --------


def test_t11_single_accession_single_span_still_not_applicable(tmp_path):
    # (a) the T2 shape: one accession, the item not presented.
    slot = _slot()
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT}, _bs_facts(slot), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell["status"] == "not_applicable"
    assert cell["na_basis"] == "not_presented_item"
    assert cell["np_footing"] == "exact"
    assert cell["np_parent_concepts"] == ["us-gaap:LiabilitiesCurrent"]
    assert cell["np_accession"] == slot["accession"]
    assert ctx.counters.get("np_span_not_requested") is None
    assert ctx.counters.get("np_alias_fact_other_accession") is None
    assert ctx.counters.get("np_outcome:not_presented") == 1

    # (b) a duration-period metric whose single own span (371 days = 53 fiscal
    # weeks) is exactly the span the census requests.
    governed = {"us-gaap:Revenues"}
    own_span = ("2025-06-25", "2026-06-30")
    st_duration = _np_metric("short_term_debt", "SyntheticShortTermDebtLine", kind="duration")
    facts = _bs_facts(slot, extra=[
        ("us-gaap", "Revenues", "USD",
         [_fact(slot["accession"], "2026-06-30", val=9, start=own_span[0])]),
    ])
    assert w._np_requested_span(facts, slot, frozenset(governed)) == own_span
    ctx = _np_ctx_governed(tmp_path / "duration", {slot["accession"]: (_NP_CAL, _NP_PRE)},
                           governed)
    cell_b = w.evaluate_cell(st_duration, {"short_term_debt": st_duration}, facts, slot,
                             recorded_at=NP_CLOCK, np_context=ctx)
    assert cell_b["status"] == "not_applicable"
    assert set(cell_b) == set(cell)
    for key in ("np_rule_id", "np_footing", "np_parent_concepts", "np_cal_sha256",
                "np_pre_sha256", "np_accession"):
        assert cell_b[key] == cell[key]
    assert ctx.counters.get("np_span_not_requested") is None
    assert ctx.counters.get("np_outcome:not_presented") == 1


# T12-T14 (defect 1 broadened): the served precondition refuses NP for a
# visible alias fact in ANY unit from ANY accession, not only other-accession
# USD; an EUR or shares fact at the report date made served print
# NOT_EVALUABLE (unexpected_unit) where the writer printed not_applicable.


def test_t12_other_accession_eur_alias_fact_keeps_the_absent_result(tmp_path):
    slot = _slot()
    other = _accn(1, 42)
    leaked_eur = ("us-gaap", "SyntheticShortTermDebtLine", "EUR",
                  [_fact(other, slot["report_date"], val=5000)])
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT},
                           _bs_facts(slot, extra=[leaked_eur]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert ctx.counters.get("np_alias_fact_other_accession") == 1


def test_t13_other_accession_shares_alias_fact_keeps_the_absent_result(tmp_path):
    slot = _slot()
    other = _accn(1, 42)
    leaked_shares = ("us-gaap", "SyntheticShortTermDebtLine", "shares",
                     [_fact(other, slot["report_date"], val=5000)])
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT},
                           _bs_facts(slot, extra=[leaked_shares]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert ctx.counters.get("np_alias_fact_other_accession") == 1


def test_t14_own_accession_eur_alias_fact_keeps_the_absent_result(tmp_path):
    slot = _slot()
    # No USD alias fact anywhere: the only alias fact at the report date is an
    # EUR one filed by the slot's own accession, which the strict pass cannot
    # match (wrong unit) and served would print NOT_EVALUABLE for.
    own_eur = ("us-gaap", "SyntheticShortTermDebtLine", "EUR",
               [_fact(slot["accession"], slot["report_date"], val=5000)])
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT},
                           _bs_facts(slot, extra=[own_eur]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_no_alias_fact"}
    assert ctx.counters.get("np_alias_fact_other_accession") == 1


# T15 (defect 1 broadened, formula funnel): an operand that fails the alias
# gate is OTHER, so the formula keeps its existing absent_dependency result.


def test_t15_formula_operand_with_eur_alias_fact_keeps_absent_dependency(tmp_path):
    slot = _slot()
    other = _accn(1, 42)
    leaked_eur = ("us-gaap", "SyntheticShortTermDebtLine", "EUR",
                  [_fact(other, slot["report_date"], val=5000)])
    cash_entry = ("us-gaap", "CashAndCashEquivalentsAtCarryingValue", "USD",
                  [_fact(slot["accession"], slot["report_date"], val=250000)])
    specs = {
        "short_term_debt": _ST_DEBT,
        "long_term_debt_current": _LTD_CURRENT,
        "long_term_debt": _LTD,
        "total_debt": _formula_spec(
            "total_debt",
            ("short_term_debt", "long_term_debt_current", "long_term_debt"),
            _TOTAL_DEBT_POLICY,
        ),
    }
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(specs["total_debt"], specs,
                           _bs_facts(slot, extra=[cash_entry, leaked_eur]), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell == {"status": "absent", "reason_code": "absent_dependency"}
    assert ctx.counters.get("np_alias_fact_other_accession") == 1


# T16 (regression): the broadened gate changes no single-accession verdict.


def test_t16_regression_single_accession_item_not_presented_still_np(tmp_path):
    slot = _slot()
    ctx = _np_ctx(tmp_path, {slot["accession"]: (_NP_CAL, _NP_PRE)})
    cell = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT}, _bs_facts(slot), slot,
                           recorded_at=NP_CLOCK, np_context=ctx)
    assert cell["status"] == "not_applicable"
    assert (cell["reason_code"], cell["kernel_reason"]) == ("not_presented", "not_presented")
    assert cell["na_basis"] == "not_presented_item"
    assert cell["np_rule_id"] == "not_presented.short_term_debt/v1"
    assert cell["np_accession"] == slot["accession"]
    assert cell["np_cal_sha256"] == hashlib.sha256(_NP_CAL).hexdigest()
    assert cell["np_pre_sha256"] == hashlib.sha256(_NP_PRE).hexdigest()
    assert cell["np_footing"] == "exact"
    assert cell["np_parent_concepts"] == ["us-gaap:LiabilitiesCurrent"]
    assert set(cell) == {
        "status", "reason_code", "kernel_reason", "na_basis",
        "np_kind", "np_rule_id", "np_rule_version", "np_rules_sha256",
        "np_parent_concepts", "np_roles_checked", "np_children_n",
        "np_children_with_fact_n", "np_footing", "np_cal_sha256", "np_pre_sha256",
        "np_accession",
    }
    assert ctx.counters.get("np_alias_fact_other_accession") is None
    assert ctx.counters.get("np_span_not_requested") is None
    assert ctx.counters.get("np_outcome:not_presented") == 1

    # A USD alias fact in the slot's own accession at the report date matches
    # the strict pass, so evaluate_cell returns present before any NP gate:
    # admitting own accessions into the gate cannot suppress a present cell.
    own_usd = ("us-gaap", "SyntheticShortTermDebtLine", "USD",
               [_fact(slot["accession"], slot["report_date"], val=5000)])
    strict = w.evaluate_cell(_ST_DEBT, {"short_term_debt": _ST_DEBT},
                             _bs_facts(slot, extra=[own_usd]), slot, {},
                             recorded_at=NP_CLOCK, np_context=ctx)
    assert strict == {"status": "present", "reason_code": "present"}


# T17 (frozen-spec item 2): malformed units levels are skipped, never raised.


def test_t17_malformed_units_levels_are_skipped_never_raise():
    slot = _slot()
    other = _accn(1, 42)
    malformed = {
        "not-a-payload": "nope",
        "us-gaap": {
            "SyntheticShortTermDebtLine": {"units": {
                "EUR": "not-a-list",
                "shares": [_fact(other, slot["report_date"])],
            }},
            "UnrelatedConcept": {"units": "not-a-dict"},
        },
    }
    # The any-unit walk skips the malformed EUR list and still fires on the
    # well-formed shares list; no level raises.
    assert w._np_alias_fact_other_accession(_ST_DEBT, malformed, slot) is True
    only_malformed = {
        "not-a-payload": "nope",
        "us-gaap": {
            "SyntheticShortTermDebtLine": {"units": {"EUR": "not-a-list"}},
            "UnrelatedConcept": {"units": "not-a-dict"},
        },
    }
    assert w._np_alias_fact_other_accession(_ST_DEBT, only_malformed, slot) is False
