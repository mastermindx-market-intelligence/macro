"""Leader-side line-by-line comparison of DC_FIXTURE_DESK.json against DC_FIXTURE_LEADER.json.
Usage: python3 compare_dc_fixture.py <desk.json> <leader.json> <out.txt>"""
import json, sys
D = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2]))
cmap = {"P": "P_packed_from_0", "R": "R_ruleA_first_kept_draw"}
out, nf, bad = [], 0, []
def eq(tag, a, b):
    global nf
    nf += 1
    ok = a == b
    out.append(f"{'OK ' if ok else 'DIFF'} {tag}: desk={a} leader={b}")
    if not ok: bad.append(tag)
seen = set()
for r in D["rows"]:
    lc = L["conventions"][cmap[r["convention"]]][r["case_id"]]; tag = f"{r['case_id']}/{r['convention']}"
    seen.add((r["case_id"], r["convention"]))
    if "admissible_k" not in lc:
        eq(tag + " defined", bool(r.get("n_admissible") or 0), False); continue
    eq(tag + " observed", r["runs_observed"], lc["observed_runs"])
    eq(tag + " #adm", r["n_admissible"], lc["n_admissible"])
    eq(tag + " excluded", r["excluded_k"], lc["excluded_k"])
    eq(tag + " k_nearest_half", r["k_nearest_half"], lc["k_nearest_half"])
    eq(tag + " runs_nearest_half", r["shifted_runs_at_nearest_half"], lc["runs_at_nearest_half"])
    if r["k_min_admissible"]:
        eq(tag + " runs_at_kmin", r["shifted_runs_at_k_min"], lc["runs_at_kmin"])
    else:
        out.append(f"NOTE {tag} K_min=5 not admissible on both? desk flag False, leader first admissible k={lc['k_at_kmin']} (5 in leader excluded: {5 in lc['excluded_k']})")
missing = [(c, cv) for cv, cs in (("P", "P_packed_from_0"), ("R", "R_ruleA_first_kept_draw")) for c in L["conventions"][cs] if c != "E_all_wrap" and (c, cv) not in seen]
out.append(f"leader cases with no desk row: {missing}")
e = L["conventions"]["P_packed_from_0"]["E_all_wrap"]
eq("e observed", D["case_e"]["runs_observed"], e["observed_runs"]); eq("e #adm", D["case_e"]["n_admissible"], e["n_admissible"]); eq("e excluded", D["case_e"]["excluded_k"], e["excluded_k"])
for b in D["production_boundary"]:
    eq(f"prod n={b['n']}", b["n_candidate_k"], L["prod_kmin_check"][str(b["n"])]["n_admissible"])
out.append(f"FIELDS {nf} DIFF {len(bad)} {bad}")
open(sys.argv[3], "w").write("\n".join(out) + "\n"); print("\n".join(out[-6:]))
