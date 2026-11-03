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
