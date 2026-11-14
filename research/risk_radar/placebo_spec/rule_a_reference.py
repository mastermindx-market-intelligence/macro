"""Rule A reference placement (PLACEBO_PLACEMENT_SPEC_v1 §2, co-signed). Placement only; no scoring."""
import json, sys
import numpy as np


def admissible(a: np.ndarray, E: np.ndarray, ln: int) -> np.ndarray:
    n = len(a)
    if ln > n:
        return np.array([], dtype=int)
    occ = np.concatenate([[0], np.cumsum(a)])
    ss = np.arange(0, n - ln + 1)
    lo, hi = np.maximum(0, ss - 1), np.minimum(n, ss + ln + 1)
    return ss[E[ss] & ((occ[hi] - occ[lo]) == 0)]


def place(runs, E, *, n_draws, seed, cap=None):
    """runs in index order. Returns dict with kept draws (list of [start, len] sorted by start)."""
    E = np.asarray(E, dtype=bool); n = len(E)
    cap = 10 * n_draws if cap is None else cap
    M = int(sum(runs))
    if not E.any():
        return {"attempts": 0, "kept": 0, "discarded": 0, "defined": False, "draws": []}
    rng = np.random.default_rng(seed)
    kept, att = [], 0
    while len(kept) < n_draws and att < cap:
        att += 1
        a = np.zeros(n, dtype=bool); placed = []; ok = True
        for ln in rng.permutation(np.asarray(runs, dtype=int)):
            ln = int(ln); c = admissible(a, E, ln)
            if not len(c):
                ok = False; break
            s = int(c[rng.integers(0, len(c))]); a[s:s + ln] = True; placed.append([s, ln])
        if ok:
            assert int(a.sum()) == M and sorted(l for _, l in placed) == sorted(runs)
            kept.append(sorted(placed))
    return {"attempts": att, "kept": len(kept), "discarded": att - len(kept),
            "defined": len(kept) == n_draws, "draws": kept}


def _mask(n, spec):
    E = np.zeros(n, dtype=bool)
    if spec == "all": E[:] = True
    elif spec == "none": pass
    else: E[spec["from"]:spec["to"] + 1] = True
    return E


if __name__ == "__main__":
    fx = json.load(open(sys.argv[1]))
    out = {}
    for c in fx["cases"]:
        r = place(c["runs_index_order"], _mask(c["n"], c["eligible"]),
                  n_draws=fx["n_draws"], seed=fx["seed"], cap=fx["cap"])
        out[c["id"]] = {"attempts": r["attempts"], "discarded": r["discarded"], "kept": r["kept"],
                        "defined": r["defined"], "first3_runs_start_len": r["draws"][:3]}
    print(json.dumps(out, indent=1))
