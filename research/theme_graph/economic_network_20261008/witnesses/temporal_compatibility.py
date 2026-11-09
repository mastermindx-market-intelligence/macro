#!/usr/bin/env python3
"""Research witness using byte-exact pinned Data OS code; no production edits.

Run: python witnesses/temporal_compatibility.py
The synthetic clock rows exercise incumbent helper semantics only. They are not
registered owner datasets, real relationship evidence, or historical system replay.
ThemeState and held K3D are SOURCE_TRACED, not executed or replicated.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def file_receipt(root, entry):
    source = root / entry["local"]
    raw = source.read_bytes()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    digest = hashlib.sha256(raw).hexdigest()
    if git_blob != entry["blob"] or digest != entry["sha256"]:
        raise RuntimeError("Pinned source integrity mismatch: " + entry["path"])
    return dict(entry, verified_git_blob=git_blob, verified_sha256=digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "temporal_compatibility_results.json")
    args = parser.parse_args()
    entries = json.loads((HERE / "source_manifest.json").read_text())
    receipts = [file_receipt(HERE, entry) for entry in entries]
    temporal_entry = next(e for e in entries if e["path"] == "lib/dataos/temporal.py")
    temporal_path = HERE / temporal_entry["local"]
    name = "gmi_research_pinned_dataos_temporal"
    spec = importlib.util.spec_from_file_location(name, temporal_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load pinned temporal source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    results = []

    def check(case_id, method, inputs, invoke, expected, reason):
        try:
            actual = invoke()
            passed = actual == expected
            result = {"case_id": case_id, "execution": "EXECUTED_PINNED_SOURCE",
                      "method": method, "inputs": inputs, "expected": expected,
                      "actual": actual, "status": "PASS" if passed else "FAIL",
                      "interpretation": reason}
        except Exception as exc:
            result = {"case_id": case_id, "execution": "EXECUTED_PINNED_SOURCE",
                      "method": method, "inputs": inputs, "expected": expected,
                      "exception": {"type": type(exc).__name__, "message": str(exc)},
                      "status": "FAIL", "interpretation": reason}
        results.append(result)

    def refusal(invoke):
        try:
            invoke()
        except module.TemporalError as exc:
            return {"type": type(exc).__name__, "refused": True}
        return {"refused": False}

    instant = "2026-10-08T08:00:00Z"
    cutoff = "2026-10-08T12:00:00Z"
    profile_names = ["BARS", "REVISABLE_RELEASE", "SNAPSHOT_SERIES", "EVENT"]
    for profile_name in profile_names:
        profile = module.TemporalProfile[profile_name]
        row = {"published_at": instant, "ingested_at": "2026-10-08T20:00:00Z"}
        check(profile_name + "_published_precedence", "known_at", row,
              lambda row=row, profile=profile: module.known_at(row, profile).isoformat(),
              "2026-10-08T08:00:00+00:00",
              "Publication takes precedence over later ingestion. This helper defines profile knowability, not proof the actual system had ingested the row then.")
        check(profile_name + "_publication_filter", "as_of_filter",
              {"profile": profile_name, "row": row, "cutoff": cutoff},
              lambda row=row, profile=profile: len(module.as_of_filter([row], cutoff, profile)),
              1, "The incumbent publication-clock coalesce allows this helper row before its later ingestion; do not describe this as historical system replay.")
        fallback = {"published_at": None, "ingested_at": "2026-10-08T10:00:00Z"}
        check(profile_name + "_ingestion_fallback", "known_at", fallback,
              lambda row=fallback, profile=profile: module.known_at(row, profile).isoformat(),
              "2026-10-08T10:00:00+00:00",
              "Null publication falls back to ingestion under the declared profile.")
    check("same_day_date_string_refused", "known_at",
          {"published_at": "2026-10-08", "ingested_at": instant, "profile": "EVENT"},
          lambda: refusal(lambda: module.known_at(
              {"published_at": "2026-10-08", "ingested_at": instant}, module.TemporalProfile.EVENT)),
          {"type": "TemporalError", "refused": True},
          "Date-only nonnull publication is rejected, not converted to midnight or bypassed by ingestion fallback.")
    check("date_object_refused", "utc", {"python_date": "2026-10-08"},
          lambda: refusal(lambda: module.utc(date(2026, 10, 8))),
          {"type": "TemporalError", "refused": True},
          "A calendar date cannot prove an instant.")
    check("naive_datetime_refused", "utc", {"naive_datetime": "2026-10-08T08:00:00"},
          lambda: refusal(lambda: module.utc(datetime(2026, 10, 8, 8))),
          {"type": "TemporalError", "refused": True},
          "No implicit UTC/timezone assumption.")
    offset_row = {"id": "offset_equal", "published_at": "2026-10-08T10:00:00+02:00"}
    later_row = {"id": "one_microsecond_later", "published_at": "2026-10-08T08:00:00.000001Z"}
    check("exact_utc_cutoff_inclusive", "as_of_filter",
          {"rows": [offset_row, later_row], "cutoff": instant, "profile": "EVENT"},
          lambda: [r["id"] for r in module.as_of_filter(
              [offset_row, later_row], instant, module.TemporalProfile.EVENT)],
          ["offset_equal"], "Normalize offsets, include equality, exclude even one microsecond later.")
    check("before_exact_cutoff_excluded", "as_of_filter",
          {"row": offset_row, "cutoff": "2026-10-08T07:59:59.999999Z"},
          lambda: len(module.as_of_filter(
              [offset_row], "2026-10-08T07:59:59.999999Z", module.TemporalProfile.EVENT)),
          0, "One microsecond before the lawful instant cannot include the row.")
    intelligence = {"published_at": instant, "ingested_at": instant,
                    "computed_at": instant, "served_at": "2026-10-08T13:00:00Z"}
    check("intelligence_served_clock", "known_at",
          {"profile": "INTELLIGENCE", "row": intelligence},
          lambda: module.known_at(intelligence, module.TemporalProfile.INTELLIGENCE).isoformat(),
          "2026-10-08T13:00:00+00:00",
          "INTELLIGENCE uses served_at; publication, ingestion, and computation cannot substitute for it.")
    check("intelligence_before_served_excluded", "as_of_filter",
          {"profile": "INTELLIGENCE", "row": intelligence, "cutoff": cutoff},
          lambda: len(module.as_of_filter([intelligence], cutoff, module.TemporalProfile.INTELLIGENCE)),
          0, "Before actual served_at this artifact is not replayable via this helper.")
    check("intelligence_missing_served_refused", "known_at",
          {"published_at": instant, "ingested_at": instant, "profile": "INTELLIGENCE"},
          lambda: refusal(lambda: module.known_at(
              {"published_at": instant, "ingested_at": instant}, module.TemporalProfile.INTELLIGENCE)),
          {"type": "PointInTimeError", "refused": True},
          "Promised replay clock must be present, even when other clocks exist.")
    derived = dict(intelligence, code_version="research-synthetic", input_cutoffs={})
    check("derived_pit_refused_even_with_clocks", "as_of_filter",
          {"profile": "DERIVED", "row": derived, "cutoff": cutoff},
          lambda: refusal(lambda: module.as_of_filter([derived], cutoff, module.TemporalProfile.DERIVED)),
          {"type": "PointInTimeError", "refused": True},
          "Extra publication/ingestion/served clocks do not silently change DERIVED's registered profile.")
    check("derived_empty_input_still_refused", "as_of_filter",
          {"profile": "DERIVED", "rows": [], "cutoff": cutoff},
          lambda: refusal(lambda: module.as_of_filter([], cutoff, module.TemporalProfile.DERIVED)),
          {"type": "PointInTimeError", "refused": True},
          "Profile guard runs before touching rows; empty input does not legitimize PIT.")
    check("missing_event_clocks_refused", "known_at", {"profile": "EVENT", "row": {}},
          lambda: refusal(lambda: module.known_at({}, module.TemporalProfile.EVENT)),
          {"type": "PointInTimeError", "refused": True},
          "Unanswerable knowability is explicit refusal, not silent omission.")
    schema_entry = next(e for e in entries if e["path"].endswith("propagation_hypothesis.v1.schema.json"))
    schema = json.loads((HERE / schema_entry["local"]).read_text())
    description = schema["properties"]["asof"]["description"]
    # This verifies a source declaration exists, not an executed composer path.
    if "DATE-granular" not in description or "intraday on the cutoff date" not in description:
        raise RuntimeError("Pinned K3D source declaration changed unexpectedly")
    traces = [
        {"surface": "held K3D candidate", "execution": "SOURCE_TRACED_NOT_EXECUTED",
         "ref": schema_entry["ref"], "source_path": schema_entry["path"],
         "source_location": "properties.asof.description; freeze clock law and validator _date_key/K3D_R061",
         "declared_rule": description,
         "interpretation": "A DATE cutoff cannot be represented as an intraday cut such as 12:00Z. Same-day evidence is admitted by its declared date rule. This is compatibility evidence, not a demonstrated defect against that held contract, and not production/live proof."},
        {"surface": "current ThemeState", "execution": "SOURCE_TRACED_NOT_EXECUTED",
         "ref": temporal_entry["ref"], "source_path": "engine/theme_graph/theme_state.py",
         "source_locations": ["_clock", "_proven_by", "_clock_reasons"],
         "traced_behavior": {"same_day_date_at_intraday_cutoff": "KNOWLEDGE_TIME_UNPROVEN",
                             "prior_day_date_at_intraday_cutoff": "date interval completed before cutoff day",
                             "precise_instant_at_equal_cutoff": "eligible on <= comparison"},
         "interpretation": "Traced directly from pinned source; this script does not import ThemeState or execute guessed replicas. Its DATE rule differs from DataOS utc, which refuses DATE entirely, and from held K3D's declared DATE cutoff."},
    ]
    output = {
        "schema": "gmi.research.temporal_compatibility_witness/v1",
        "authority": "RESEARCH_FIXTURE_ONLY_NO_OWNER_PROFILE_OR_CLOCK_CHANGE",
        "inputs": "Synthetic clock rows; no real economic relationships or registered-dataset admission.",
        "python": platform.python_version(), "executable_status": "EXECUTED_PINNED_DATAOS_SOURCE",
        "source_receipts": receipts, "cases": results, "source_traces": traces,
        "summary": {"executed_cases": len(results),
                    "passed": sum(r["status"] == "PASS" for r in results),
                    "failed": sum(r["status"] == "FAIL" for r in results),
                    "theme_state": "SOURCE_TRACED_NOT_EXECUTED",
                    "k3d": "SOURCE_TRACED_NOT_EXECUTED"},
        "limitations": [
            "Generic helper behavior is not full schema/registry/owner dataset validation.",
            "Publication-clock eligibility is not ingestion proof or historical system replay.",
            "INTELLIGENCE helper checks served_at only; full artifact-required fields and log custody were not validated.",
            "No ThemeState state producer, natural generation, K3D positive-path composer, network, portfolio, or live consumer was executed.",
            "No guessed clock helper or replica is treated as canonical."
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output["summary"], sort_keys=True))
    return 1 if output["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

