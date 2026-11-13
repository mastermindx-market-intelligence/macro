"""Independent leader-side fixture reading of DISPLACED_CLOCK_v1_1.md (7ffc9ba7…).

Placement only: admissible shifts, wrap/merge exclusions and shifted series. No scoring,
no real alert, no outcome. Reads the shared Rule A fixture for n and runs.

Usage: python3 dc_fixture_reference.py <placebo_fixture_v1.json> <out.json>
"""
import json
import sys

import numpy as np

FIXTURE_KMIN = 5          # page: fixture-only value
PROD_KMIN = 63            # page: max(63, pre + post_max + 1) with pre 21, post_max 10 -> 63


def runs_of(a):
    out, i, n = [], 0, len(a)
    while i < n:
        if a[i]:
            j = i
            while j < n and a[j]:
                j += 1
            out.append([i, j - i])
            i = j
        else:
            i += 1
    return out


def series(n, starts_lens):
    a = np.zeros(n, dtype=bool)
    for s, ln in starts_lens:
        a[s:s + ln] = True
    return a


def shift(a, k):
    # page: a'(t) = a((t - k) mod n)  ==  np.roll(a, k)
    return np.roll(a, k)


def admissible(a, kmin):
    n = len(a)
    want = sorted(ln for _, ln in runs_of(a))
    adm, excl = [], []
    for k in range(kmin, n - kmin + 1):
        (adm if sorted(ln for _, ln in runs_of(shift(a, k))) == want else excl).append(k)
    return adm, excl


def case_out(n, sl, kmin):
    a = series(n, sl)
    adm, excl = admissible(a, kmin)
    out = {"n": n, "observed_runs": sl, "kmin": kmin, "k_range": [kmin, n - kmin],
           "admissible_k": adm, "excluded_k": excl, "n_admissible": len(adm),
           "defined_nonempty": bool(adm)}
    if adm:
        k_lo = kmin if kmin in adm else adm[0]
        k_mid = min(adm, key=lambda k: (abs(k - n / 2), k))   # nearest n/2, ties to lower k
        out["k_at_kmin"] = k_lo
        out["runs_at_kmin"] = runs_of(shift(a, k_lo))
        out["k_nearest_half"] = k_mid
        out["runs_at_nearest_half"] = runs_of(shift(a, k_mid))
    return out


def main(fx_path, out_path):
    fx = json.load(open(fx_path))
    res = {"page_sha256": "7ffc9ba76d9e9bc6313769bbc15f5fa5531af1be4589738adba45eb5087910e4",
           "conventions": {}, "prod_kmin_check": {}}
    # Convention P (packed): runs in index order, first at session 0, one OFF session between.
    # Convention R (Rule A first kept draw from the fixture's expected block; F4 has none).
    conv_p, conv_r = {}, {}
    for c in fx["cases"]:
        n, runs = c["n"], c["runs_index_order"]
        s, sl = 0, []
        for ln in runs:
            sl.append([s, ln]); s += ln + 1
        conv_p[c["id"]] = case_out(n, sl, FIXTURE_KMIN)
        first = fx["expected"][c["id"]]["first3_runs_start_len"]
        conv_r[c["id"]] = case_out(n, first[0], FIXTURE_KMIN) if first else {"n": n, "note": "no kept draw"}
    # (e): one run of 32 at session 4 in n=40. Shifted starts 9..39 all give start+32 > 40,
    # so every k in [5,35] wraps; it must read "not defined".
    e = case_out(40, [[4, 32]], FIXTURE_KMIN)
    assert e["n_admissible"] == 0
    conv_p["E_all_wrap"] = e; conv_r["E_all_wrap"] = e
    res["conventions"]["P_packed_from_0"] = conv_p
    res["conventions"]["R_ruleA_first_kept_draw"] = conv_r
    # production K_min: defined set must be empty whenever n < 2*K_min
    chk = {}
    for n in (40, 100, 125, 126, 127, 200):
        a = series(n, [[1, 3]])
        adm, _ = admissible(a, PROD_KMIN)
        chk[str(n)] = {"n_lt_2kmin": n < 2 * PROD_KMIN, "n_admissible": len(adm)}
        assert (n < 2 * PROD_KMIN) == (len(adm) == 0)
    res["prod_kmin_check"] = chk
    json.dump(res, open(out_path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
