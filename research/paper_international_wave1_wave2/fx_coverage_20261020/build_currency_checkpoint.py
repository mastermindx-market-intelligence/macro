#!/usr/bin/env python3
"""Bind currency implementation evidence without advancing Git or publication."""
from __future__ import annotations
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FISCAL = ROOT / "research/paper_international_wave1_wave2/fiscal_coverage_20261019"
CANONICAL = ROOT / "mockups/evidence/intl-currency-coverage-20261020"
CHECKPOINT = HERE / "CURRENCY_COVERAGE_20261020.json"
FROZEN = "11c83bb5dfb0c8199a0fb0cb2c6e70452c724984"
REMOTE = "88b6f192c3e2a7a94f5cf7ff4d9d06bc225324a4"
def sha(data):
    return hashlib.sha256(data).hexdigest()
def read(path):
    return json.loads(path.read_text())
def fp(path):
    path = ROOT / path
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}
def verify(entry):
    actual = fp(entry["path"])
    assert actual["sha256"] == entry["sha256"], entry["path"]
    if "bytes" in entry:
        assert actual["bytes"] == entry["bytes"], entry["path"]
    return actual

head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
assert head == FROZEN, head
for rel in ("engine/intl_inputs.py", "collectors/intl_prices.py"):
    delta = subprocess.check_output(["git", "diff", FROZEN, "--", rel], cwd=ROOT)
    assert not delta, rel
parents = {
    "config/intl_country_baseline.json": "43e16a0f1dfc20aec4efc3b866437063e28da2ffadfd57465428973b92daba27",
    "app/deploy/Caddyfile": "eb0abf17c03d1ef5ab2c6378ac67d6dfb71b58b5353810af64a08c4629780190",
    "config/site_access.yml": "127dd1de71c979910601a8df89132244e95c0d1991c194408281072ace6384c9",
    "tests/test_site_access_boundary.py": "220d3790b2a0135b7ea1b8c75a1d0a68192d9e3082a72168c39b8850da5372cf",
    str((FISCAL / "FISCAL_COVERAGE_20261020.json").relative_to(ROOT)): "9dbb0e2f6bc05d052a5fa1173a38fd79f765a4e79951832c86c0a40d1d5b0064",
    str((FISCAL / "fiscal_source_snapshot.tar.gz").relative_to(ROOT)): "c44d73d2fbfc858a08eae3e017adcd3e766078f0ffb87ca9b59411b897a255ab",
    str((FISCAL / "paper_fiscal_coverage_receipt.json").relative_to(ROOT)): "d2ddabaad3798809af2daccf0fc3beffa92422060d3741024dd9e6aa5a496231",
}
parent_files = [verify({"path": p, "sha256": h}) for p, h in parents.items()]
source = read(HERE / "source_qualification.json")
assert source["passed"] and source["canonical_store_writes"] == 0
assert len(source["countries"]) == 7
for country in source["countries"]:
    raw = gzip.decompress((HERE / country["raw_archive"]).read_bytes())
    assert sha(raw) == country["response_sha256"], country["cc"]
    assert country["expected"]["end"]["date"] == "2026-10-19"
    assert country["expected"]["start"]["date"] == "2026-07-17"
    assert country["timestamp_rows"] == 133 and country["valid_quotes"] == 132
assert fp("tests/fixtures/intl_currency_observations_20261020.json")["sha256"] == source["fixture_sha256"]
assert sha((HERE / "preview/currency_replay.json").read_bytes()) == source["currency_replay_sha256"]
paper = read(HERE / "paper_currency_coverage_receipt.json")
assert fp(HERE / "paper_currency_coverage_receipt.json")["sha256"] == "79997eaa36f432ed03baa28fae53fc75ba46ca932c72da2732858183c55d50dc"
assert paper["effect_count_including_finish"] == paper["original_response_retained_count"] == 6
for entry in paper["effects"] + paper["artifacts"]:
    verify(entry)
readback = read(HERE / "paper_final_readback_verification.json")
assert readback["text_count"] == readback["text_passed"] == 20
assert readback["style_count"] == readback["style_passed"] == 12
assert readback["order_count"] == readback["order_passed"] == 4
materialized = read(HERE / "paper_capture_materialization.json")
verify(materialized["native_bundle"])
assert sha(gzip.decompress((ROOT / materialized["native_bundle"]["path"]).read_bytes())) == materialized["decompressed_sha256"]
preview = read(HERE / "preview/manifest.json")
for name, digest in preview["html_sha256"].items():
    assert sha((HERE / "preview" / name).read_bytes()) == digest
    entry = preview["html_archives"][name]
    verify(entry)
    assert sha(gzip.decompress((ROOT / entry["path"]).read_bytes())) == digest
browser = read(HERE / "browser_verification.json")
assert browser["country_checks"] == browser["passed"] == 84
assert browser["ageing_passed"] == len(browser["ageing_controls"]) == 8
assert browser["page_errors"] == []
assert len(browser["history"]) == 2 and all(x["passed"] for x in browser["history"])
assert browser["html_sha256"] == preview["html_sha256"]["intl_integrated_preview.html"]
assert sha((ROOT / browser["canonical_manifest"]).read_bytes()) == browser["canonical_manifest_sha256"]
for item in browser["checks"]:
    expected_font = "17px" if item["viewport"] == "desktop" else "15px"
    assert item["trendFont"] == item["trendTextFont"] == expected_font
for item in browser["screenshots"]:
    verify(item)
canonical = read(CANONICAL / "manifest.json")
assert canonical["totals"]["states_captured"] == canonical["totals"]["states_attempted"] == 12
for page in canonical["pages"]:
    for state in page["states"]:
        if state["captured"]:
            verify({"path": str((CANONICAL / state["file"]).relative_to(ROOT)),
                    "sha256": state["sha256"], "bytes": state["bytes"]})
gates = read(HERE / "gates/verification.json")
assert gates["passed"] and gates["frozen_head"] == FROZEN
for key in ("paper_receipt", "preview_manifest", "browser"):
    verify(gates[key])
for gate in gates["gates"]:
    assert gate["exit_code"] == 0
    verify(gate["log"])
ci = read(HERE / "ci_dependency_coverage.json")
assert ci["passed"] and ci["input_bytes_unchanged"]
assert ci["import_closure_findings"] == {} and ci["unwired_suites"] == []
for entry in ci["inputs"]:
    verify(entry)
final_gates = read(HERE / "gates/final_catalogue_and_whitespace.json")
assert final_gates["passed"]
tests = read(HERE / "country_and_public_tests.json")
assert tests["returncode"] == 0
assert "298 passed" in (HERE / tests["log"]).read_text()
source_paths = [
    ".github/ci/legacy-jobs.yml", "lib/intl_currency_observation.py",
    "lib/intl_country_assessment.py", "engine/intl_run.py",
    "templates/intl_country_cockpit.html.j2", "templates/intl_country_cockpit.css",
    "templates/intl_country_cockpit.js", "tests/test_intl_currency_observation.py",
    "tests/test_intl_country_cockpit.py", "tests/fixtures/intl_currency_observations_20261020.json",
    "research/paper_international_wave1_wave2/preview_country_cockpit.py",
    "research/paper_international_wave1_wave2/capture_country_cockpit.py",
    "agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md",
    "engine/intl_inputs.py", "collectors/intl_prices.py",
]
integrity = {
    "schema": "mastermind.intl_currency_evidence_integrity.v1",
    "recorded_at": datetime.now(timezone.utc).isoformat(), "passed": True,
    "frozen_head": head, "qualified_response_archives": 7, "paper_original_effects": 6,
    "paper_text_checks": 20, "paper_style_checks": 12, "paper_order_checks": 4,
    "browser_country_checks": 84, "browser_ageing_checks": 8, "browser_font_checks": 84,
    "canonical_captures": 12, "lossless_html_archives": 3,
    "legacy_fx_inputs_and_collector_unchanged": True, "parent_files": parent_files,
    "scope": "Current working-tree source and retained evidence bytes; no publication or production verdict."
}
(HERE / "integrity.json").write_text(json.dumps(integrity, indent=2) + "\n")
files = {ROOT / p for p in source_paths}
files.update(ROOT / p for p in parents)
files.add(FISCAL / "fiscal_source_snapshot.json")
for directory in (HERE, CANONICAL):
    files.update(p for p in directory.rglob("*") if p.is_file()
                 and p != CHECKPOINT and not p.name.startswith("pr_")
                 and p.name not in ("completion.json",)
                 and "__pycache__" not in p.parts)
fingerprints = [fp(p) for p in sorted(files)]
checkpoint = {
    "schema": "mastermind.intl_currency_coverage_checkpoint.v1",
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "operation": "intl-country-cockpit-20261018", "workspace": str(ROOT),
    "branch": "sol/web-intl-country-cockpit-20261018", "frozen_local_head": head,
    "last_observed_remote_head": REMOTE,
    "pr": "https://github.com/mastermindx-market-intelligence/macro/pull/9596",
    "state": "IMPLEMENTED_AND_LOCALLY_VERIFIED__PUBLICATION_FENCED",
    "source_qualification": source,
    "verification": {"selected_python_cases_passed": 298, "currency_cases_within_selection": 80,
                     "browser_country_cases_passed": 84, "explicit_ageing_controls_passed": 8,
                     "browser_font_checks_passed": 84, "canonical_states_captured": 12,
                     "canonical_ci_dependency_findings": ci["import_closure_findings"],
                     "unwired_suites": ci["unwired_suites"], "integrity": fp(HERE / "integrity.json")},
    "paper": {"receipt": fp(HERE / "paper_currency_coverage_receipt.json"),
              "file_id": paper["file_id"], "page_id": paper["page_id"], "url": paper["url"],
              "original_applied_effects": 6, "text_checks": 20, "style_checks": 12, "order_checks": 4},
    "html_sha256": preview["html_sha256"], "fiscal_parent_files": parent_files,
    "publication_fence": {
        "action_ref": "d07df7c6e45d35c54338808701350ece97c605401ad69a0fd28bb415d05a5a56",
        "state": "EFFECT_UNKNOWN / PUSH_RESULT_UNCERTAIN",
        "last_owner_check": "2026-10-20T01:52:43Z",
        "required_resolution": "Canonical classification by the original C2 publisher owner before commit/push continuation.",
        "not_authorized_by_this_receipt": ["advancing_HEAD", "push_replay", "alternate_publisher", "Ready", "merge", "deploy", "restart"]
    },
    "limits": [
        "Held working-tree increment is absent from the last observed remote PR head.",
        "Retained quote qualification does not populate the canonical FX store or prove production observations.",
        "Equity replay remains dated 15 October; currency snapshot ends 19 October; render time is separate.",
        "Browser proof uses anonymous isolated integrated HTML; live_config, blocked analytics and authenticated/degraded-state gaps remain explicit.",
        "Current-snapshot CI inference is not hosted combined-source PR-versus-base contract-delta.",
        "Hosted CI, genuine Sector Central Full RIG approvals, Session Bridge/formal independent release review, normal render/updater and actual served acceptance remain required.",
        "PR8754 retains its separate rights, browser, Saved and release obligations."
    ],
    "file_count": len(fingerprints), "files": fingerprints,
    "metadata_maintenance": "PR body effect and final re-verification are recorded separately to avoid cyclic hashes."
}
CHECKPOINT.write_text(json.dumps(checkpoint, indent=2) + "\n")
print(json.dumps({"passed": True, "checkpoint": fp(CHECKPOINT), "files_bound": len(fingerprints),
                  "integrity": fp(HERE / "integrity.json")}))
