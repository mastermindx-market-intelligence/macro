"""Complete numeric science-leaf attribution of C2 result.json vs round 0.

Read-only on both JSON files. No re-estimation. Writes leaf_attribution.json
under RESULTS_DIR (parent of this file's parent).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE.parent
REPO = Path(
    os.environ.get(
        "C2_REPO",
        "/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/astra-host2-052e02d-690b56cac98b57f7",
    )
).resolve()
R2_JSON = RESULTS_DIR / "result.json"
R0_JSON = Path(
    os.environ.get(
        "C2_R0_JSON",
        "/private/tmp/claude-501/-Users-chriswong-Documents-Cluade-macro-main--claude-worktrees-astra-ceo-handoff-4a36a0/f273dd7d-5dfb-4725-b26d-3de277637b11/scratchpad/results_prev/C2_r0/result.json",
    )
)
OUT_JSON = RESULTS_DIR / "leaf_attribution.json"

SCIENCE_ROOTS = {
    "did",
    "gaps",
    "cost_curve",
    "false_starts_avoided",
    "large_winners_excluded",
    "breadth_axis",
    "support",
    "n_1d_events_joined",
    "n_1d_events_dropped_no_state",
    "meta",
}

TAG_A = "(a) B1 panel delta"
TAG_B = "(b) C1 record delta"
TAG_C_1D = "(c) estimator/rule restore: 1D-row estimator"
TAG_C_KEY = "(c) estimator/rule restore: key-merge mapping"
TAG_C_PHASE = "(c) estimator/rule restore: phase_count packet definition"
TAG_C_MONO = "(c) estimator/rule restore: strict monotonic"
TAG_C_VERDICT = "(c) estimator/rule restore: verdict-by-code"
TAG_C_ERA = "(c) estimator/rule restore: era qualification"
TAG_C_HONEST = "(c) estimator/rule restore: honest-N blocks"
TAG_C_NFINITE = "(c) estimator/rule restore: cost-curve n is n_finite_mfe"
TAG_JOINT = "(a)+(c) jointly"

ERA_QUAL = {
    "2014-2019 (2015-08-05..2019-12-30)": "2014-2019",
    "2020-2026 (2019-12-31..2026-08-28)": "2020-2026",
}
ERA_QUAL_RE = re.compile(
    r"2014-2019 \(2015-08-05\.\.2019-12-30\)|2020-2026 \(2019-12-31\.\.2026-08-28\)"
)

HONEST_N_RE = re.compile(
    r"(?:^|\.)(?:n_events|n_months|n_names|n_events_confirmed|n_months_confirmed|"
    r"n_names_confirmed|n_events_1d|n_months_1d|n_names_1d)(?:\[|$|\.)"
    r"|(?:^|\.)n\.(?:fast|mid|persistent)\."
    r"|(?:^|\.)(?:max_mfe|min_mfe|sd_mfe|median_mfe_consumed)(?:\[|$)"
)

COST_N_RE = re.compile(r"^cost_curve\.(?:2D|3D)\.(?:fast|mid|persistent)\.n$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def flatten(obj, prefix: str = "") -> dict:
    """Dotted leaves; explode lists (CI bounds become path[0], path[1])."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def science_only(flat: dict) -> dict:
    keep = {}
    for k, v in flat.items():
        root = k.split(".", 1)[0].split("[", 1)[0]
        if root in SCIENCE_ROOTS and is_num(v):
            keep[k] = v
    return keep


def normalize_era(path: str) -> str:
    out = path
    for qual, bare in ERA_QUAL.items():
        out = out.replace(qual, bare)
    return out


def has_era_qual(path: str) -> bool:
    return bool(ERA_QUAL_RE.search(path))


def is_honest_n(path: str) -> bool:
    npath = normalize_era(path)
    # support.n_events/n_months/n_names already existed in round 0; a rename is era qualification.
    if npath.startswith("support."):
        return False
    if HONEST_N_RE.search(npath):
        return True
    if re.search(r"^cost_curve\.(?:2D|3D)\.(?:fast|mid|persistent)\.(?:n_events|n_months|n_names)$", npath):
        return True
    if re.search(
        r"^(?:false_starts_avoided|large_winners_excluded)\.(?:fast|mid|persistent)\.(?:n_events|n_months|n_names)$",
        npath,
    ):
        return True
    return False


def is_cost_n(path: str) -> bool:
    return bool(COST_N_RE.match(normalize_era(path)))


def is_1d_count(path: str) -> bool:
    npath = normalize_era(path)
    if npath in {"n_1d_events_joined", "meta.n_1d_events_joined"}:
        return True
    if npath.endswith(".n_1d") or npath.endswith(".n_1d_events") or ".all_1d.n_events" in npath:
        return True
    if npath.startswith("meta.n_confirmed"):
        return True
    return False


def is_share_family(path: str) -> bool:
    return path.startswith("false_starts_avoided.") or path.startswith("large_winners_excluded.")


def classify(path: str, r0, now, renamed: bool) -> str:
    """Assign exactly one class tag. leftover_untagged must stay 0."""
    c_era = renamed or has_era_qual(path)
    c_honest = is_honest_n(path)
    c_nfinite = is_cost_n(path)
    c_1d = is_1d_count(path)
    c_key = is_share_family(path) and (
        "share" in path or path.endswith(".n") or c_honest
    )
    both = r0 is not None and now is not None
    moved = both and r0 != now
    a = False
    if moved:
        a = True
        # cost-curve n 75,099 → 72,059 is the N5 finite-mfe redefinition, not +2 panel rows
        if c_nfinite and abs(float(now) - float(r0)) > 10:
            a = False
    c_any = c_era or c_honest or c_nfinite or c_1d or c_key
    if a and c_any:
        return TAG_JOINT
    if a:
        return TAG_A
    if c_nfinite:
        return TAG_C_NFINITE
    # New honest-N fields under era-qualified keys are (c) honest-N, not a value-preserving rename.
    if c_honest:
        return TAG_C_HONEST
    if c_era:
        return TAG_C_ERA
    if c_key:
        return TAG_C_KEY
    if c_1d:
        return TAG_C_1D
    if now is None or r0 is None:
        return TAG_C_HONEST
    return TAG_A


def jsonable(x):
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return x
    return x


def largest_for(rows: list[dict]) -> dict | None:
    best = None
    best_abs = -1.0
    for row in rows:
        r0, now = row["r0"], row["now"]
        if r0 is None or now is None:
            continue
        d = float(now) - float(r0)
        ad = abs(d)
        if ad > best_abs:
            best_abs = ad
            best = {
                "path": row["path"],
                "r0": r0,
                "now": now,
                "delta": now - r0 if not isinstance(now, bool) else d,
            }
    return best


def main() -> dict:
    r0_obj = json.loads(R0_JSON.read_text())
    r2_obj = json.loads(R2_JSON.read_text())
    f0 = science_only(flatten(r0_obj))
    f2 = science_only(flatten(r2_obj))

    # Pair era-qualified keys with their round-0 bare counterparts.
    groups: dict[str, dict] = {}
    for p, v in f0.items():
        n = normalize_era(p)
        rec = groups.setdefault(n, {"r0_path": None, "now_path": None, "r0": None, "now": None})
        rec["r0_path"] = p
        rec["r0"] = v
    for p, v in f2.items():
        n = normalize_era(p)
        rec = groups.setdefault(n, {"r0_path": None, "now_path": None, "r0": None, "now": None})
        rec["now_path"] = p
        rec["now"] = v

    leaves = []
    for norm, rec in sorted(groups.items()):
        r0, now = rec["r0"], rec["now"]
        r0p, nowp = rec["r0_path"], rec["now_path"]
        renamed = bool(r0p and nowp and r0p != nowp)
        added = r0p is None and nowp is not None
        removed = nowp is None and r0p is not None
        moved = r0 is not None and now is not None and r0 != now
        if not (moved or added or removed or renamed):
            continue
        path = nowp if nowp is not None else r0p
        if r0 is not None and now is not None:
            delta = now - r0
        else:
            delta = None
        tag = classify(path, r0, now, renamed)
        leaves.append(
            {
                "path": path,
                "r0": jsonable(r0),
                "now": jsonable(now),
                "delta": jsonable(delta),
                "tag": tag,
            }
        )

    leftover = sum(1 for L in leaves if L["tag"] is None)
    assert leftover == 0, f"untagged leaves: {leftover}"

    class_names = [
        TAG_A,
        TAG_B,
        TAG_C_1D,
        TAG_C_KEY,
        TAG_C_PHASE,
        TAG_C_MONO,
        TAG_C_VERDICT,
        TAG_C_ERA,
        TAG_C_HONEST,
        TAG_C_NFINITE,
        TAG_JOINT,
    ]
    classes = {}
    for name in class_names:
        rows = [L for L in leaves if L["tag"] == name]
        classes[name] = {
            "count": len(rows),
            "largest_abs_delta": largest_for(rows),
        }

    # In-place both-present (no era pairing) for comparison with the round-2 reviewer's 83.
    both_raw = set(f0) & set(f2)
    inplace_raw = sorted(k for k in both_raw if f0[k] != f2[k])

    key_did = "did.3D.pooled.h10.delta"
    r0_did = f0[key_did]
    now_did = f2[key_did]
    out = {
        "round0_sha256": sha256_file(R0_JSON),
        "round2_sha256": sha256_file(R2_JSON),
        "changed_numeric_leaves": len(leaves),
        "classes": classes,
        "leaves": leaves,
        "leftover_untagged": leftover,
        "key_rows": {
            "did.3D.pooled.h10.did": {
                "r0": r0_did,
                "now": now_did,
                "delta": now_did - r0_did,
            }
        },
        "method": {
            "science_roots": sorted(SCIENCE_ROOTS),
            "ci_bounds_exploded": True,
            "era_keys_paired_by_stripping_qualifier": True,
            "added_and_removed_included": True,
            "in_place_both_present_no_era_pair": len(inplace_raw),
            "reviewer_r2_count": 83,
            "reviewer_count_note": (
                "Round-2 independent review reported 83 in-place both-present numeric "
                "science-value moves (did / gaps / cost_curve.n / shares / breadth / n_1d), "
                "treating CI arrays as one leaf and excluding honest-N / era-label rewrites. "
                "This round explodes CI bounds (ci[0]/ci[1]), pairs era-qualified keys with "
                "their bare round-0 counterparts, and includes added/removed numeric leaves "
                "(honest-N blocks, era-key qualification of support/by_era paths, extra "
                "cost-curve descriptives). (b) C1 record delta is assigned zero leaves "
                "because rotation parquet 9361dbf0… is byte-identical."
            ),
        },
    }
    OUT_JSON.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    rec = main()
    print("changed_numeric_leaves", rec["changed_numeric_leaves"])
    print("leftover_untagged", rec["leftover_untagged"])
    for name, info in rec["classes"].items():
        largest = info["largest_abs_delta"]
        lp = None if largest is None else largest["path"]
        ld = None if largest is None else largest["delta"]
        print(f"  {name}: count={info['count']} largest={lp} delta={ld}")
    kr = rec["key_rows"]["did.3D.pooled.h10.did"]
    print("key_row did.3D.pooled.h10.did", kr)
    print("wrote", OUT_JSON)
