#!/usr/bin/env python3
"""Verify the D04 source packet, not the application or reference acceptance.

Usage: python verify_spec.py --freeze  # create report and digest manifest
       python verify_spec.py           # verify existing frozen packet, no writes

Requires Pillow only to read actual capture dimensions. No network or product effects.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import re
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "evidence/verification_report.json"
MANIFEST = ROOT / "evidence/manifest.json"

def read(name):
    return json.loads((ROOT / name).read_text())

def close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        # Generated destinations exist before the complete relative-link audit.
        for p in (REPORT, MANIFEST):
            if not p.exists():
                p.write_text('{"status":"GENERATING"}\n')
    checks = []
    def check(name, condition, detail):
        checks.append({"check": name, "status": "PASS" if condition else "FAIL", "detail": detail})

    caps = read("capabilities.json")
    tests = read("acceptance_cases.json")
    compat = read("compatibility.json")
    boards = read("evidence/paper_boards.json")
    captures = read("evidence/captures.json")
    sources = read("evidence/source_extracts.json")
    continuity = read("review_continuity.json")
    examples = read("evidence/spec_examples.json")
    cap_ids = [r["id"] for r in caps["capabilities"]]
    test_ids = [r["id"] for r in tests["cases"]]
    expected_routes = {
        "macro:advanced", "macro:basket_family", "macro:baskets",
        "macro:confluence_screener", "macro:discovery", "macro:etfs",
        "macro:movers", "macro:sector_heatmap", "terminal:discover",
        "terminal:dislocations"}
    check("canonical route identities", {r["canonical_id"] for r in compat["canonical_routes"]} == expected_routes and len(compat["canonical_routes"]) == 10, "All ten distinct assigned IDs, no replacement by count alone.")
    check("capability IDs/counts/dispositions", len(cap_ids) == len(set(cap_ids)) == caps["count"] == 113 and dict(Counter(r["disposition"] for r in caps["capabilities"])) == caps["counts"], caps["counts"])
    check("no removals and no approval", caps["removal_count"] == 0 and all(r["disposition"] != "REMOVE" and r["reviewer_decision"].startswith("NOT_REVIEWED") for r in caps["capabilities"]), "All dispositions are proposals/retention obligations; none approved.")
    check("complete capability ownership and successor", all(r["successor"] and r["dependency"] and r["reason"] and r["baseline"]["source_section"] for r in caps["capabilities"]), "Includes all relocations and unavailable-support interim ownership.")
    check("acceptance IDs and honest execution state", len(test_ids) == len(set(test_ids)) == tests["count"] == 75 and all(r["status"] == "NOT_RUN_PRODUCT_ACCEPTANCE" and r["given"] and r["when"] and r["then"] for r in tests["cases"]), "75 future product cases; no application pass inferred.")
    linked = {t for c in caps["capabilities"] for t in c["acceptance_ids"]}
    check("capability acceptance links", all(c["acceptance_ids"] for c in caps["capabilities"]) and linked <= set(test_ids), "Every capability references defined behavioral cases.")
    check("all tests have substantive coverage", set(test_ids) <= linked | {t for c in continuity["closure"] for t in c["acceptance_ids"]} | {"D04-A062","D04-A063","D04-A064","D04-A069","D04-A071","D04-A072"}, "Cross-cutting build/performance/ownership cases are covered by build plan or continuity.")

    legacy = compat["sector_central_legacy"]
    check("24 executable legacy mappings", len(legacy) == len({r["fragment"] for r in legacy}) == compat["verified_current_legacy_count"] == 24 and Counter(r["source_table"] for r in legacy) == {"LEGACY_ANCHORS":21,"LEGACY_ANCHORS_S2":3}, "Corrects the handoff's23 count.")
    by_hash = {r["fragment"]:r for r in legacy}
    check("legacy alias targets and measured entry", by_hash["#confluence"]["target_id"] == "si-confluence" and by_hash["#si-heat-section"]["target_id"] == "theme-heat-section" and by_hash["#si-measured"]["view"] == "map", "Exact alias targets retained.")
    check("six tabs and ten analytical anchors", len(set(compat["discover_tabs"])) == 6 and len(set(compat["advanced_anchors"])) == 10, "Current Discover and Quant Lab dimensions.")
    check("49 exact basket IDs", len(sources["baskets"]["ids"]) == len(set(sources["baskets"]["ids"])) == sources["baskets"]["count"] == 49, "Current catalog receipt; no new catalog implementation.")
    check("recorded payload accounting", sources["sp500"]["calculated"]["tiles"] == 503 and sources["themes"]["calculated"]["tiles"] == 268 and sources["themes"]["calculated"]["groups"] == 40 and sources["themes"]["calculated"]["appearances"] == 2339 and sources["themes"]["calculated"]["distinct_members"] == 924 and sources["themes"]["calculated"]["measured_1d_unique_members"] == 911, "Consistency of root source-extraction receipt, not a new producer run.")
    check("1H availability override", any(r["key"] == "1H" and r["available"] is False for r in sources["sp500"]["metadata"]["timeframes"]), "A non-null value does not override unavailable metadata.")

    identities = [(r["file_id"],r["page_id"],r["artboard_id"]) for r in boards["boards"]]
    page_counts = Counter((r["file_id"],r["page_id"]) for r in boards["boards"])
    check("62 exact Paper reference identities", len(identities) == len(set(identities)) == boards["count"] == 62 and sorted(page_counts.values()) == [8,12,13,13,16], "Identity/name/dimension inventory, not62 visual approvals.")
    check("reference approval not inferred", all(r["status"] == "REFERENCE_INPUT_NOT_D04_APPROVED" and r["disposition"] == "RETAIN" for r in boards["boards"]), "No native after-design or self-approval.")
    image_errors = []
    for c in captures:
        p = ROOT / c["path"]
        if not p.is_file():
            image_errors.append(c["path"] + ": missing")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        with Image.open(p) as im:
            dims = list(im.size)
        if digest != c["sha256"] or p.stat().st_size != c["bytes"] or dims != [c["width"],c["height"]]:
            image_errors.append(c["path"] + ": hash/bytes/dimensions mismatch")
        if c.get("artboard_id") and (c["file_id"],c["page_id"],c["artboard_id"]) not in identities:
            image_errors.append(c["path"] + ": unknown Paper target")
    check("eight actual image files", len(captures) == 8 and not image_errors, image_errors or "SHA256, byte sizes, actual dimensions and Paper identity match.")
    check("25 inherited blocks preserved", len(continuity["closure"]) == continuity["count"] == 25 and len({r["id"] for r in continuity["closure"]}) == 25 and all(r["disposition"] == "CARRIED_BLOCK" and r["closure_evidence"] is None for r in continuity["closure"]), "No inherited item closed by specification prose.")
    check("continuity test references", all(set(r["acceptance_ids"]) <= set(test_ids) for r in continuity["closure"]), "Every proposed remedy references defined cases.")

    for case in examples["comparisons"]:
        b, a, threshold = case["before"], case["after"], case["threshold"]
        n = len(case["members"])
        same = [i for i in range(n) if b[i] is not None and a[i] is not None]
        def stats(values):
            observed = [v for v in values if v is not None]
            up = sum(v > threshold for v in observed)
            missing = n-len(observed)
            return up / len(observed) * 100, up/n*100, (up+missing)/n*100
        br, blo, bhi = stats(b)
        ar, alo, ahi = stats(a)
        delta = (sum(a[i] > threshold for i in same) - sum(b[i] > threshold for i in same)) / len(same) * 100
        expected = case["expected"]
        actual = {"matched_n":len(same),"matched_change_pp":delta,"before_raw_pct":br,"after_raw_pct":ar,"possible_change_pp":[alo-bhi,ahi-blo]}
        good = len(b) == len(a) == n and len(same) == expected["matched_n"] and close(delta,expected["matched_change_pp"]) and close(br,expected["before_observed_advancing_pct"]) and close(ar,expected["after_observed_advancing_pct"]) and all(close(x,y) for x,y in zip(actual["possible_change_pp"],expected["possible_change_pp"]))
        check("comparison arithmetic: "+case["id"],good,actual)
    monthly = examples["month_mean"]
    mean = sum(r["wins"]/r["fires"] for r in monthly["monthly"])/len(monthly["monthly"])*100
    pooled = sum(r["wins"] for r in monthly["monthly"])/sum(r["fires"] for r in monthly["monthly"])*100
    check("month-mean differs from pooled rate", close(mean,monthly["expected_month_mean_pct"]) and close(pooled,monthly["expected_pooled_pct"]), {"month_mean_pct":mean,"pooled_pct":pooled})
    t = examples["thresholds"]
    check("declared breadth thresholds", sum(v>0 for v in t["values_pp"]) == t["expected_strict_gt_zero"] and sum(v>0.05 for v in t["values_pp"]) == t["expected_macro_gt_005"], "Strict>0 and Macro>0.05pp produce different counts.")
    rows = [r for r in examples["capitalization"]["rows"] if r["cap"] is not None and r["cap"]>0]
    weighted = sum(r["cap"]*r["return_pct"] for r in rows)/sum(r["cap"] for r in rows)
    check("capitalization example excludes missing weight",close(weighted,examples["capitalization"]["expected_eligible_cap_weighted_pct"]),{"weighted_pct":weighted})
    shell = examples["candidate_shell"]
    def useful(w):
        nav = 224 if w>=1200 else 196 if w>860 else 0
        gutter = 16 if w<=600 else 20 if w<1200 else 24
        return w-nav-2*gutter
    actual = [useful(w) for w in shell["viewports"]]
    dock = {str(w):useful(w)-shell["dock_width"]-shell["dock_gap"] for w in [1280,1440,1600]}
    check("candidate useful widths and dock arithmetic",actual == shell["expected_useful_widths"] and dock == shell["expected_wide_with_dock"],{"widths":actual,"dock":dock,"qualification":"Not actual responsive browser or native design proof."})

    link_errors=[]
    for p in ROOT.rglob("*.md"):
        for link in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)',p.read_text()):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:",link) or link.startswith("#"):
                continue
            target = (p.parent / link.split("#")[0]).resolve()
            if not target.is_file():
                link_errors.append(str(p.relative_to(ROOT))+": "+link)
            elif ROOT not in target.parents:
                link_errors.append(str(p.relative_to(ROOT))+": outside packet "+link)
    check("relative Markdown destinations",not link_errors,link_errors or "Every local document/capture destination exists.")

    result = {
        "schema":"d04.packet_verification.v1",
        "executed_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"Artifact identity, counts, links, hashes and illustrative arithmetic only. No product application, API/DB, visual approval or model-validation execution.",
        "status":"PASS" if all(c["status"]=="PASS" for c in checks) else "FAIL",
        "check_count":len(checks),"checks":checks,
        "product_acceptance_cases_run":0,
        "rig_approval":False,
        "native_paper_writes":0,
        "manifest_policy":"Freeze writes this report first, then hashes every packet file except manifest itself. Successful verifier exit requires recomputing every manifest hash."
    }
    if result["status"]!="PASS":
        print(json.dumps(result,ensure_ascii=False,indent=2))
        raise SystemExit(1)
    if args.freeze:
        REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
        files=[]
        for p in sorted(ROOT.rglob("*")):
            if p.is_file() and p != MANIFEST and "__pycache__" not in p.parts:
                files.append({"path":str(p.relative_to(ROOT)),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()})
        manifest={"schema":"d04.artifact_manifest.v1","created_utc":datetime.now(timezone.utc).isoformat(),"classification":"SOURCE_SPECIFICATION_ARTIFACT_SET_NOT_NATIVE_AFTER_FREEZE","excluded":["evidence/manifest.json (self-reference)"],"files":files}
        MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    manifest=read("evidence/manifest.json")
    digest_errors=[]
    for entry in manifest["files"]:
        p=ROOT/entry["path"]
        if not p.is_file() or p.stat().st_size != entry["bytes"] or hashlib.sha256(p.read_bytes()).hexdigest()!=entry["sha256"]:
            digest_errors.append(entry["path"])
    actual_paths={str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file() and p!=MANIFEST and "__pycache__" not in p.parts}
    if actual_paths != {x["path"] for x in manifest["files"]}:
        digest_errors.append("manifest file-set mismatch")
    if digest_errors:
        print(json.dumps({"status":"FAIL","manifest_errors":digest_errors}))
        raise SystemExit(1)
    print(json.dumps({"status":"PASS","intrinsic_checks":len(checks),"hashed_files":len(manifest["files"]),"manifest_verified":True,"product_acceptance_cases_run":0,"report":"evidence/verification_report.json"},ensure_ascii=False))

if __name__=="__main__":
    main()

