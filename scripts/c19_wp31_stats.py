"""C19 WP31 — evaluator arms + statistics (STATS lane module).

Source of truth (PREREG wins any conflict with the build spec):
  research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md
  merged as commit 8e1950932b29f89a89da94c50ccef4ef5f2d8d1c (§0-§8 authoritative).
Frozen build spec implemented here: WP31_BUILD_SPEC.md,
  sha256 5485384ad1f08a0211f634045d23d623d7e4d961924d5b9f5911ea6081149ef1
  ("## Arms (prereg §4)" + "## Statistics (prereg §5-§6)" only; the shared episode
  dict in "## Shared episode dict" is the ONLY interface to the other two modules).

Scope of this module (prereg §4-§6): the five arms A0 / A1 / A2 / A2[-K] / A2[-S],
the descendant-aware ablation manifest assertion, common support, the primary
hit-rate delta, cluster bootstrap, exact sign test, the adjudication minimum, the
verdict table, the looks/stopping rule, the (issuer, q) uniqueness assertion, the
descriptive secondaries/splits and the descriptive economic-translation costs.

This module NEVER registers a trial budget, NEVER touches a trial ledger, NEVER
reads any file (no I/O at import time, no data/ access) and NEVER imports the
sibling WP31 modules scripts/c19_wp31_gates.py / scripts/c19_wp31_sources.py.
Registration and the G-1/G-2/G-3 gate live in the GATES lane; episode construction
lives in the SOURCES lane. Dependencies: standard library + numpy/pandas, plus a
lazy import of engine.validation inside costs() only (prereg §5 Costs).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

# --------------------------------------------------------------------------- #
# constants (prereg §5-§6, spec "Gates and registration" values the stats need)
# --------------------------------------------------------------------------- #
#: An arm's output: (sign, None) when it emits, (None, "<abstain reason>") when not.
Emission = tuple[int | None, str | None]

#: prereg §4 K-backed: "rights_class not blocked", operationalized by prereg §10
#: amendment A1 as an ALLOW-list: the label (None or empty read as UNKNOWN, compared
#: upper-cased) must be in NONBLOCKING_RIGHTS. UNKNOWN is the producer's labeled
#: absence (collectors/equity_revisions.py; engine reason SOURCE_USE_RIGHTS_UNKNOWN),
#: not a block. Every other label is blocked: the K surface's own blocked vocabulary
#: (engine/k3e_expectation_surface.py BLOCKED_RIGHTS | DISPLAY_ONLY_RIGHTS), any
#: unrecognized label, and a "MIXED:" label from two consumed rows that disagree.
#: An allow-list fails closed on a label nobody anticipated; a deny-list failed open.
NONBLOCKING_RIGHTS = frozenset({"UNKNOWN"})


def rights_blocked(rights_class: Any) -> bool:
    """True unless a K rights_class is in NONBLOCKING_RIGHTS (None/empty -> UNKNOWN)."""
    label = str(rights_class or "UNKNOWN").strip().upper() or "UNKNOWN"
    return label not in NONBLOCKING_RIGHTS

#: prereg §4 arm table. "A2-K" is A2[-K], "A2-S" is A2[-S].
ARMS = ("A0", "A1", "A2", "A2-K", "A2-S")

#: prereg §8.3 registered family, carried on every report so the seat can wire CI.
FAMILY = "c19_wp31_incremental_information"

#: prereg §8.3 registered itemized budget. N of the deflated Sharpe (prereg §5
#: "n_trials = the registered budget"). Expressed as a duck-typed fixed-budget
#: ledger, never as a literal n_trials= kwarg (see costs() / DEVIATION D1).
BUDGET = 6

#: prereg §5 Costs: benchmark per driver family.
HEDGE = {"AAPL": "XLK", "HOMEBUILDERS": "XHB"}

#: prereg §5 Costs: 10 bps per side per leg = 0.0010 * 2 sides * 2 legs.
COST_PER_EPISODE = 0.0040

#: prereg §4 K-backed staleness bound — the composer's STALE_DAYS.
_STALE_DAYS = 4

#: prereg §5 "Minimum to adjudicate".
MIN_EPISODES = 40
MIN_CLUSTERS = 12

#: prereg §5 "Useful effect": +0.10 hit rate over A2[-K]. The float is for display;
#: the verdict compares the exact rational (hits are integers, so Delta = d/n and a
#: float subtraction such as 0.6 - 0.5 = 0.0999... would turn a PASS into a NULL).
USEFUL_EFFECT = 0.10
USEFUL_EFFECT_EXACT = Fraction(1, 10)

#: prereg §5 Looks: look 2 is the first read at which common-support N reaches 80.
LOOK2_N = 80

#: prereg §5 Costs / spec: the note that must ride on the deflated Sharpe.
_NO_DECISION_WEIGHT = "no decision weight at this sample size"


class AblationError(RuntimeError):
    """prereg §4: an ablated arm's manifest contains a record of the removed family."""


# --------------------------------------------------------------------------- #
# small private helpers
# --------------------------------------------------------------------------- #
def _k(ep: Mapping[str, Any]) -> Mapping[str, Any]:
    return ep.get("k") or {}


def _s(ep: Mapping[str, Any]) -> Mapping[str, Any]:
    return ep.get("s") or {}


def _a0(ep: Mapping[str, Any]) -> Mapping[str, Any]:
    return ep.get("a0") or {}


def _ids(rec: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for rid in rec.get("record_ids") or ():
        if rid:
            out.append(str(rid))
    return out


def _utc(value: Any) -> datetime | None:
    """Parse an ISO-8601 stamp to an aware UTC datetime; None when unusable.

    Fail-closed by construction: a stamp we cannot read can never make a record
    look fresh (prereg §2.1 point-in-time reads are the leakage rule, not a hint).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _emit(value: int | None) -> Emission:
    return (int(value), None) if value is not None else (None, None)


def _abstain(reason: str) -> Emission:
    return (None, reason)


def _used_legs(arm: str, ep: Mapping[str, Any]) -> tuple[bool, bool]:
    """Which legs the arm's emitted VALUE actually came from: (uses_k, uses_s).

    prereg §4: the manifest is "the set of inputs it read" for the value reported,
    so an abstaining arm consumed nothing it would have to ablate.
    """
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}")
    if arm == "A1":
        return (arm_a1(ep)[0] is not None, False)
    if arm == "A0":
        return (False, arm_a0(ep)[0] is not None)
    if arm == "A2":
        if k_backed(ep):
            return (True, False)
        if s_backed(ep):
            return (False, True)
        return (False, False)
    if arm == "A2-K":
        return (False, arm_a2_minus_k(ep)[0] is not None)
    # "A2-S": the K leg, and nothing else (prereg §4 A2[-S] reads family K only).
    return (arm_a2_minus_s(ep)[0] is not None, False)


# --------------------------------------------------------------------------- #
# arms (prereg §4)
# --------------------------------------------------------------------------- #
def arm_a0(ep: Mapping[str, Any]) -> Emission:
    """A0 persistence (prereg §4, family S): the stored prior-filing sign, else
    ABSTAIN("no_prior_filing")."""
    sign = _a0(ep).get("sign")
    if sign is None:
        return _abstain("no_prior_filing")
    return _emit(sign)


def arm_a1(ep: Mapping[str, Any]) -> Emission:
    """A1 expectation (prereg §4, family K): sign(average - year_ago) of the §3.1
    capture group; a set abstain_reason wins, a missing value is "k_missing",
    equal values are "k_equal"."""
    k = _k(ep)
    reason = k.get("abstain_reason")
    if reason:
        return _abstain(str(reason))
    average, year_ago = k.get("average"), k.get("year_ago")
    if average is None or year_ago is None:
        return _abstain("k_missing")
    if average == year_ago:
        return _abstain("k_equal")
    return _emit(1 if average > year_ago else -1)


def k_backed(ep: Mapping[str, Any]) -> bool:
    """prereg §4 K-backed(e): A1 emits AND the group is fresh
    (system_observed_at >= C(e) - 4 days) AND expectation_state CURRENT AND the
    identity gate is CHECKED AND rights_class is not blocked AND attempt success."""
    if arm_a1(ep)[0] is None:
        return False
    k = _k(ep)
    observed, cutoff = _utc(k.get("observed_at")), _utc(ep.get("cutoff"))
    if observed is None or cutoff is None:
        return False
    if observed < cutoff - timedelta(days=_STALE_DAYS):
        return False
    if k.get("expectation_state") != "CURRENT":
        return False
    if k.get("identity_status") != "CHECKED":
        return False
    if rights_blocked(k.get("rights_class")):
        return False
    if k.get("attempt_status") != "success":
        return False
    return True


def s_backed(ep: Mapping[str, Any]) -> bool:
    """prereg §4 S-backed(e): A0 emits AND the workspace as of C(e) resolves the
    q-1 release AND the source sha256 is a non-empty string."""
    if arm_a0(ep)[0] is None:
        return False
    s = _s(ep)
    if s.get("q_minus_1_resolved") is not True:
        return False
    sha = s.get("source_sha256")
    return isinstance(sha, str) and sha != ""


def arm_a2(ep: Mapping[str, Any]) -> Emission:
    """A2 composed answer (prereg §4): A1 if K-backed, else A0 if S-backed, else
    ABSTAIN("no_backing")."""
    if k_backed(ep):
        return arm_a1(ep)
    if s_backed(ep):
        return arm_a0(ep)
    return _abstain("no_backing")


def arm_a2_minus_k(ep: Mapping[str, Any]) -> Emission:
    """A2[-K] (prereg §4): the composed answer with the expectation family removed,
    i.e. A0 if S-backed else ABSTAIN("no_s_backing"). Family K is fully ablated:
    no K leg, feature or gate is read (see assert_ablation)."""
    if s_backed(ep):
        return arm_a0(ep)
    return _abstain("no_s_backing")


def arm_a2_minus_s(ep: Mapping[str, Any]) -> Emission:
    """A2[-S] (prereg §4): the composed answer with the SEC family (and its
    descendants) removed, i.e. A1 if K-backed else ABSTAIN("no_k_backing")."""
    if k_backed(ep):
        return arm_a1(ep)
    return _abstain("no_k_backing")


#: arm -> implementation (prereg §4 table).
_ARM_FUNCS = {
    "A0": arm_a0,
    "A1": arm_a1,
    "A2": arm_a2,
    "A2-K": arm_a2_minus_k,
    "A2-S": arm_a2_minus_s,
}


def emit(arm: str, ep: Mapping[str, Any]) -> Emission:
    """Dispatch an arm name in ARMS over the shared episode dict."""
    try:
        fn = _ARM_FUNCS[arm]
    except KeyError:
        raise ValueError(f"unknown arm {arm!r}; expected one of {ARMS}") from None
    return fn(ep)


def manifest(arm: str, ep: Mapping[str, Any]) -> frozenset[str]:
    """prereg §4: the per-arm input manifest — the record ids the arm actually
    consumed for the value it emitted. K record_ids when A1's value is used;
    S record_ids plus the a0 accession when A0's value is used. The label is never
    part of a manifest (prereg §4: "The label is never ablated")."""
    uses_k, uses_s = _used_legs(arm, ep)
    ids: set[str] = set()
    if uses_k:
        ids.update(_ids(_k(ep)))
    if uses_s:
        ids.update(_ids(_s(ep)))
        accession = _a0(ep).get("accession")
        if accession:
            ids.add(str(accession))
    return frozenset(ids)


def assert_ablation(ep: Mapping[str, Any]) -> None:
    """prereg §4 descendant-aware ablation rule: the evaluator must assert that an
    ablated arm's manifest contains no record of the removed family.

    A2[-K] must show no K-family record id; A2[-S] must show no S-family record id
    and no a0 accession (the accession is the S leg's filing index — an SEC
    descendant). Violation raises AblationError; the label is never ablated, so no
    label check exists here.
    """
    k_ids = set(_ids(_k(ep)))
    s_ids = set(_ids(_s(ep)))
    accession = _a0(ep).get("accession")
    if accession:
        s_ids.add(str(accession))
    leak_k = manifest("A2-K", ep) & k_ids
    if leak_k:
        raise AblationError(
            f"A2[-K] manifest leaks K-family records for "
            f"({ep.get('issuer')}, {ep.get('q')}): {sorted(leak_k)}")
    leak_s = manifest("A2-S", ep) & s_ids
    if leak_s:
        raise AblationError(
            f"A2[-S] manifest leaks S-family records for "
            f"({ep.get('issuer')}, {ep.get('q')}): {sorted(leak_s)}")


# --------------------------------------------------------------------------- #
# common support + the primary statistic (prereg §4-§5)
# --------------------------------------------------------------------------- #
def common_support(episodes: Iterable[Mapping[str, Any]]) -> list[dict]:
    """prereg §4 Common support (primary): status ELIGIBLE, label in {+1, -1}, and
    A2[-K] emits (S-backed).

    EXPOSED and NOT_EVALUABLE episodes are excluded from every reported statistic
    (prereg §0 "Prospective only, no backfill"; §6 exposure accounting).
    """
    rows: list[dict] = []
    for ep in episodes:
        if ep.get("status") != "ELIGIBLE":
            continue
        if ep.get("label") not in (1, -1):
            continue
        if arm_a2_minus_k(ep)[0] is None:
            continue
        rows.append(dict(ep))
    return rows


def hits(arm: str, rows: Sequence[Mapping[str, Any]]) -> int:
    """The integer count of rows whose arm sign equals Y(e); an abstention is not a hit."""
    count = 0
    for row in rows:
        sign, _ = emit(arm, row)
        if sign is not None and sign == row.get("label"):
            count += 1
    return count


def hit_rate(arm: str, rows: Sequence[Mapping[str, Any]]) -> float | None:
    """HR(arm, rows) (prereg §5): the fraction of rows whose arm sign equals Y(e).
    An abstention is not a hit. None on empty rows."""
    if not rows:
        return None
    return hits(arm, rows) / len(rows)


def primary_delta_exact(rows: Sequence[Mapping[str, Any]]) -> Fraction | None:
    """prereg §5 primary statistic as an exact rational:
    Delta = (hits(A2) - hits(A2[-K])) / n on common support. None on empty rows.
    The verdict's +0.10 comparison uses this value, never a float difference."""
    if not rows:
        return None
    return Fraction(hits("A2", rows) - hits("A2-K", rows), len(rows))


def primary_delta(rows: Sequence[Mapping[str, Any]]) -> float | None:
    """prereg §5 primary statistic: Delta = HR(A2) - HR(A2[-K]) on common support,
    as a float for display and the bootstrap (its interval is compared with 0 only).
    A2 always emits on common support (A2[-K] emitting implies S-backed)."""
    exact = primary_delta_exact(rows)
    return None if exact is None else float(exact)


def cluster_key(ep: Mapping[str, Any]) -> tuple[str, str]:
    """prereg §6 Clusters: (calendar quarter of t_rel as "YYYYQn", driver family).
    An unreadable t_rel keys as "UNKNOWN" — fail-closed, never a silent drop."""
    dt = _utc(ep.get("t_rel"))
    if dt is None:
        quarter = "UNKNOWN"
    else:
        quarter = f"{dt.year}Q{(dt.month - 1) // 3 + 1}"
    return (quarter, str(ep.get("cluster")))


def _clusters_rows(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault(cluster_key(row), []).append(dict(row))
    return groups


def bootstrap_interval(rows: Sequence[Mapping[str, Any]], *, seed: int = 31,
                       B: int = 2000) -> tuple[float, float] | None:
    """prereg §5 Uncertainty: cluster bootstrap over clusters, B = 2000, seed 31,
    percentile (2.5, 97.5) interval on Delta. None when there are no rows.

    S3 determinism: numpy.random.default_rng(seed) is created INSIDE this function
    per call, so two calls over the same rows return identical intervals. Each
    replicate draws len(clusters) cluster keys WITH replacement from the sorted list
    of distinct cluster keys and recomputes Delta on the pooled rows. A replicate
    whose pooled rows are empty is skipped: it carries no statistic and reporting a
    None as a 0.0 delta would bias the interval — in practice pooling cannot be
    empty (every cluster holds at least one row), so the guard is belt-and-braces.
    """
    if not rows:
        return None
    groups = _clusters_rows(rows)
    keys = sorted(groups)
    pooled_by_key = [groups[key] for key in keys]
    rng = np.random.default_rng(seed)
    deltas: list[float] = []
    for _ in range(int(B)):
        picks = rng.integers(0, len(keys), size=len(keys))
        pooled: list[dict] = []
        for idx in picks:
            pooled.extend(pooled_by_key[int(idx)])
        if not pooled:  # skipped replicate: no rows, therefore no Delta (see above)
            continue
        delta = primary_delta(pooled)
        if delta is None:
            continue
        deltas.append(float(delta))
    if not deltas:
        return None
    low, high = np.percentile(np.asarray(deltas, dtype=float), [2.5, 97.5])
    return (float(low), float(high))


# --------------------------------------------------------------------------- #
# exact sign test on the discordant pairs (prereg §5)
# --------------------------------------------------------------------------- #
def sign_test_p(b: int, c: int) -> float:
    """Exact two-sided sign-test p on discordant counts (prereg §5):
    n = b + c, p = min(1, 2 * sum_{i=0..min(b,c)} C(n, i) / 2**n); n == 0 -> 1.0.
    math.comb only — no scipy (lane law S4)."""
    n = int(b) + int(c)
    if n == 0:
        return 1.0
    smaller = min(int(b), int(c))
    tail = sum(math.comb(n, i) for i in range(smaller + 1))
    return min(1.0, 2.0 * tail / (2.0 ** n))


def discordant(rows: Sequence[Mapping[str, Any]]) -> dict:
    """prereg §5: b = #(A2 right, A2[-K] wrong), c = #(A2 wrong, A2[-K] right), with
    the exact two-sided p. Printed alongside Delta, as descriptive."""
    b = c = 0
    for row in rows:
        a2, _ = emit("A2", row)
        a2k, _ = emit("A2-K", row)
        label = row.get("label")
        if label not in (1, -1):
            continue
        right_a2 = a2 is not None and a2 == label
        right_a2k = a2k is not None and a2k == label
        if right_a2 and not right_a2k:
            b += 1
        elif right_a2k and not right_a2:
            c += 1
    return {"b": b, "c": c, "p": sign_test_p(b, c)}


# --------------------------------------------------------------------------- #
# adjudication minimum, verdict table, looks (prereg §5)
# --------------------------------------------------------------------------- #
def minimum_met(n: int, n_clusters: int) -> bool:
    """prereg §5: at least 40 common-support episodes AND at least 12 clusters."""
    return int(n) >= MIN_EPISODES and int(n_clusters) >= MIN_CLUSTERS


def _exact(delta: Fraction | float | int) -> Fraction:
    """A Fraction passes through; an int or float converts exactly (a float keeps its
    binary value, so callers deciding the +0.10 boundary pass primary_delta_exact)."""
    return delta if isinstance(delta, Fraction) else Fraction(delta)


def verdict(n: int, n_clusters: int, delta: Fraction | float | None,
            interval: tuple[float, float] | None) -> tuple[str, str]:
    """prereg §5 verdict table (the rows partition every outcome; first match wins).

    | INCONCLUSIVE    | minimum not met                                        |
    | PASS_FOR_REVIEW | minimum met, Delta >= +0.10, 2.5th pct > 0           |
    | ADVERSE         | minimum met, 97.5th pct < 0                          |
    | NULL            | minimum met, not ADVERSE, Delta < +0.10              |
    | INCONCLUSIVE    | minimum met, Delta >= +0.10, 2.5th pct <= 0          |

    Delta exactly +0.10 is a PASS candidate, not a NULL (>= / < split, prereg
    "Useful effect"); the comparison is exact (USEFUL_EFFECT_EXACT against the
    rational Delta), so 24/40 against 20/40 is a PASS candidate. The reason strings
    for rows 2-5 are not fixed by the prereg or the spec; these wordings name the
    matched condition (reported in GAPS).
    """
    if not minimum_met(n, n_clusters):
        return ("INCONCLUSIVE", "minimum_not_met")
    if delta is None or interval is None:
        return ("INCONCLUSIVE", "no_common_support_statistics")
    p25, p975 = float(interval[0]), float(interval[1])
    useful = _exact(delta) >= USEFUL_EFFECT_EXACT
    if p25 > 0.0 and useful:
        return ("PASS_FOR_REVIEW", "delta_ge_useful_effect_and_interval_excludes_zero")
    if p975 < 0.0:
        return ("ADVERSE", "interval_below_zero")
    if not useful:
        return ("NULL", "delta_below_useful_effect")
    return ("INCONCLUSIVE", "delta_ge_useful_effect_but_interval_includes_zero")


def classify_look(n: int, n_clusters: int,
                  prior_reads: Sequence[Mapping[str, Any]]) -> str:
    """Classify the current read. The ordered rules (1)-(4) below are the spec's
    READING of this prereg §6 paragraph, quoted verbatim (lane law S2; the prereg is
    authoritative):

        "**Looks.** At most two adjudicating looks: look 1 is the first read at which the minimum
        is met; look 2 is the first read at which common-support episodes reach 80. The
        family-wise one-sided error for each direction is 5%, split equally across the two looks
        (Bonferroni), so each look's decision interval is the 2.5th-97.5th bootstrap percentile.
        Look 1 stops the study only on `PASS_FOR_REVIEW` or `ADVERSE`; otherwise the study
        continues to look 2, whose verdict is terminal. If one read first meets both thresholds,
        it is look 2 and there is no separate look 1. Every other read is descriptive monitoring
        and cannot stop the study."
    """
    reads = list(prior_reads or ())
    # (1) a read that stopped the study: every later read is descriptive monitoring.
    if any(bool(r.get("study_stopped")) for r in reads):
        return "monitoring"
    # (2) N >= 80 with no prior look2: look2 is terminal, and the minimum still binds
    #     (a look2 with clusters < 12 is INCONCLUSIVE "minimum_not_met").
    if int(n) >= LOOK2_N and not any(r.get("look") == "look2" for r in reads):
        return "look2"
    # (3) the first read at which the adjudication minimum is met is look1.
    if minimum_met(n, n_clusters) and not any(
            r.get("look") in ("look1", "look2") for r in reads):
        return "look1"
    # (4) every other read is monitoring.
    return "monitoring"


def is_study_stopped(look: str, verdict_: str) -> bool:
    """prereg §5 Looks: look 1 stops only on PASS_FOR_REVIEW or ADVERSE; look 2 is
    terminal whatever it says."""
    return (look == "look1" and verdict_ in ("PASS_FOR_REVIEW", "ADVERSE")) or look == "look2"


# --------------------------------------------------------------------------- #
# sample-dependence guard + descriptive accounting (prereg §6)
# --------------------------------------------------------------------------- #
def assert_unique(episodes: Iterable[Mapping[str, Any]]) -> None:
    """prereg §6: "Independent N is episodes, never rows" — exactly one row per
    (issuer, q). A duplicate raises."""
    seen: set[tuple[Any, Any]] = set()
    dupes: list[tuple[Any, Any]] = []
    for ep in episodes:
        key = (ep.get("issuer"), ep.get("q"))
        if key in seen and key not in dupes:
            dupes.append(key)
        seen.add(key)
    if dupes:
        raise ValueError(f"duplicate (issuer, q) episodes: {sorted(map(str, dupes))}")


def secondaries(episodes: Iterable[Mapping[str, Any]]) -> dict:
    """prereg §6 Secondary contrasts (descriptive, no verdict): HR(A1) - HR(A0)
    where both emit and the label is +/-1; coverage and HR of A2[-S] versus A2[-K]
    over ELIGIBLE +/-1-label episodes; and the primary Delta split by driver family
    (from splits())."""
    rows = [dict(ep) for ep in episodes if ep.get("status") == "ELIGIBLE"
            and ep.get("label") in (1, -1)]
    both = [r for r in rows
            if emit("A1", r)[0] is not None and emit("A0", r)[0] is not None]
    hr_a1 = hit_rate("A1", both)
    hr_a0 = hit_rate("A0", both)
    out: dict[str, Any] = {
        "hr_a1_minus_hr_a0": {
            "n": len(both),
            "hr_a1": hr_a1,
            "hr_a0": hr_a0,
            "delta": None if (hr_a1 is None or hr_a0 is None) else hr_a1 - hr_a0,
        },
        "a2_minus_s_vs_a2_minus_k": {},
    }
    for arm in ("A2-S", "A2-K"):
        emitting = [r for r in rows if emit(arm, r)[0] is not None]
        out["a2_minus_s_vs_a2_minus_k"][arm] = {
            "coverage": (len(emitting) / len(rows)) if rows else None,
            "n_emit": len(emitting),
            "hr": hit_rate(arm, emitting),
        }
    out["a2_minus_s_vs_a2_minus_k"]["n_eligible_labeled"] = len(rows)
    cs = common_support(rows)
    split = splits(cs)
    out["split_aapl"] = split["AAPL"]
    out["split_homebuilders"] = split["HOMEBUILDERS"]
    return out


def splits(rows: Sequence[Mapping[str, Any]]) -> dict:
    """prereg §6: the primary Delta split by driver family (AAPL; HOMEBUILDERS),
    flagged as tiny-N. The prereg states the flag for the splits as such, so
    "tiny_n" is the constant True on both subsets (basis items 5 and 6)."""
    out: dict[str, Any] = {}
    for family in ("AAPL", "HOMEBUILDERS"):
        subset = [r for r in rows if r.get("cluster") == family]
        keys = {cluster_key(r) for r in subset}
        out[family] = {
            "n": len(subset),
            "n_clusters": len(keys),
            "delta": primary_delta(subset),
            "tiny_n": True,
        }
    return out


class _FixedBudget:
    """Duck-typed ledger carrying the registered itemized budget as N (DEVIATION D1).

    engine/trial_ledger.py:595 documents exactly this shape: "ratchet-clean
    stand-in for a bare ``deflated_sharpe(n_trials=n)`` where the count [is
    mandated]" — deflated_sharpe(..., ledger=TrialLedger.with_declared_budget(n, fam),
    family=fam). Here N is the prereg §8.3 constant 6, so the ledger object is a
    fixed-budget stub with effective_n(family) == BUDGET. This module never touches
    a real ledger and never registers (S5); passing ledger= + family= is what
    tests/test_no_literal_ntrials.py requires instead of the literal kwarg the spec
    text ("deflated_sharpe(..., n_trials=6, ...)") spells out.
    """

    def effective_n(self, family: str | None) -> int:  # noqa: ARG002 (duck-typed API)
        return BUDGET


def _pearson_moments(series: Sequence[float]) -> tuple[float, float, float, int]:
    """(per-period Sharpe, skew, Pearson kurtosis, n) computed with numpy only.

    Mirrors engine/validation.py:202-203 ret_moments, whose docstring fixes the
    kurtosis convention that deflated_sharpe consumes — quoted verbatim:
        "(per-period Sharpe, skew, Pearson-kurtosis, n) of a return series — the
         inputs the DSR consumes. Pearson kurtosis (normal = 3), ddof=1 like sharpe()."
    So kurtosis here is RAW/Pearson (normal = 3), NOT excess kurtosis: engine/
    validation.py:298 uses var_scaler = 1 - skew*sr + ((kurt - 1)/4)*sr**2, which is
    the Bailey & Lopez de Prado / Lo (2002) form only under the raw convention
    (kurt = 3 gives 1 + sr**2/2). numpy default ddof=0 is NOT used; the denominator
    is std(ddof=1), like ret_moments.
    """
    r = np.asarray(series, dtype=float)
    r = r[~np.isnan(r)]
    n = int(r.size)
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    sr = mu / sd
    z = (r - mu) / sd
    return sr, float((z ** 3).mean()), float((z ** 4).mean()), n


def costs(rows: Sequence[Mapping[str, Any]]) -> dict:
    """prereg §5 Costs (secondary, descriptive only): economic translation of A2.

    pnl = sign(A2) * (ret_issuer - ret_hedge) - 0.0040 for every common-support
    episode carrying "returns" (10 bps per side per leg = 2 sides x 2 legs; the
    repository default cost_bps = 0 is explicitly not used). Benchmarks: XLK for
    AAPL, XHB for the homebuilders (HEDGE). Reported mean and n. The deflated
    Sharpe is printed only when engine.validation.bootstrap_effective_t returns a
    non-empty dict (it returns {} when n < max(3*block, 60), engine/validation.py:231,
    or when the bootstrap variance is non-positive); otherwise "insufficient_n" is
    recorded and deflated_sharpe is never called (lane law S1). The note
    "no decision weight at this sample size" always rides along (prereg §5).
    """
    pnls: list[float] = []
    n_missing_returns = 0
    n_no_sign = 0
    for row in rows:
        rets = row.get("returns")
        if not rets:
            n_missing_returns += 1
            continue
        sign, _ = emit("A2", row)
        if sign is None:
            n_no_sign += 1
            continue
        pnls.append(float(sign) * (float(rets["ret_issuer"]) - float(rets["ret_hedge"]))
                    - COST_PER_EPISODE)
    out: dict[str, Any] = {
        "cost_per_episode": COST_PER_EPISODE,
        "benchmarks": dict(HEDGE),
        "n_rows": len(rows),
        "n_pnl": len(pnls),
        "n_without_returns": n_missing_returns,
        "n_without_a2_sign": n_no_sign,
        "mean": float(np.mean(pnls)) if pnls else None,
        "deflated_sharpe": "insufficient_n",
        "note": _NO_DECISION_WEIGHT,
    }
    if pnls:
        # Lazy import: engine.validation is only needed on the (long) path where the
        # bootstrap is computable, and it is pure numpy/pandas with no import-time I/O.
        from engine.validation import bootstrap_effective_t, deflated_sharpe

        arr = np.asarray(pnls, dtype=float)
        eff = bootstrap_effective_t(arr, block=21, B=2000)
        if eff:
            sr, skew, kurt, n_obs = _pearson_moments(arr)
            t_eff = int(eff["t_eff"])
            # DEVIATION D1: prereg §5 fixes N as "the registered budget" (6). The spec
            # writes it as deflated_sharpe(..., n_trials=6, ...); tests/test_no_literal_ntrials.py
            # blocks a literal n_trials= caller in scripts/, so the same N is expressed
            # through the honest path as ledger=/family= with a fixed-budget stub.
            dsr = deflated_sharpe(sr, skew, kurt, n_obs, ledger=_FixedBudget(),
                                  family=FAMILY, t_eff=t_eff)
            out["deflated_sharpe"] = {"inputs": {"sr_period": sr, "skew": skew,
                                                  "kurtosis_pearson": kurt, "T": n_obs,
                                                  "t_eff": t_eff, "family": FAMILY,
                                                  "n_trials": BUDGET},
                                      "dsr": dsr}
        else:
            out["deflated_sharpe"] = "insufficient_n"
    return out


# --------------------------------------------------------------------------- #
# the report every read prints (prereg §6 "Every read prints")
# --------------------------------------------------------------------------- #
def build_report(episodes: Iterable[Mapping[str, Any]],
                 prior_reads: Sequence[Mapping[str, Any]] = ()) -> dict:
    """Assemble the full read. Every key prereg §6 / the spec's "Report dict keys"
    bullet demands is present on every read, including a read with no common
    support (counts print next to zeros, never beside a dropped field).

    prereg §6: eligible episodes; EXPOSED exclusions; each NOT_EVALUABLE reason with
    its count; each arm's emit count and ABSTAIN reasons; common-support N; cluster
    count; Delta with interval; discordant pair counts and p; secondary contrasts;
    per-family splits; costs; family and budget.

    Monitoring reads (prereg §5 Looks) "report their numbers descriptively but never
    change the study verdict": they carry the stopping read's verdict when a prior
    read stopped the study, otherwise "MONITORING".
    """
    eps = [dict(ep) for ep in episodes]
    assert_unique(eps)          # prereg §6: independent N is episodes, never rows
    reads = [dict(r) for r in (prior_reads or ())]
    for ep in eps:
        if ep.get("status") == "ELIGIBLE":
            assert_ablation(ep)  # prereg §4: descendant-aware ablation assertion

    eligible = [ep for ep in eps if ep.get("status") == "ELIGIBLE"]
    exposed = sum(1 for ep in eps if ep.get("status") == "EXPOSED")
    not_evaluable: dict[str, int] = {}
    for ep in eps:
        if ep.get("status") != "NOT_EVALUABLE":
            continue
        reason = ep.get("not_evaluable_reason") or "unspecified"
        not_evaluable[str(reason)] = not_evaluable.get(str(reason), 0) + 1

    arms: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        emit_count = 0
        abstain: dict[str, int] = {}
        for ep in eligible:
            sign, reason = emit(arm, ep)
            if sign is not None:
                emit_count += 1
            else:
                key = reason or "unspecified"
                abstain[key] = abstain.get(key, 0) + 1
        arms[arm] = {"emit": emit_count, "abstain": abstain}

    rows = common_support(eps)
    n = len(rows)
    n_clusters = len({cluster_key(row) for row in rows})
    delta_exact = primary_delta_exact(rows)
    delta = None if delta_exact is None else float(delta_exact)
    interval = bootstrap_interval(rows)
    look = classify_look(n, n_clusters, reads)
    if look == "monitoring":
        stopped = [r for r in reads if r.get("study_stopped")]
        if stopped:
            study_verdict = stopped[-1].get("verdict")
            verdict_reason = "monitoring_carries_stopping_verdict"
            # The study stopped at an earlier read; carrying its verdict while
            # reporting study_stopped False would contradict the report itself.
            study_stopped = True
        else:
            study_verdict = "MONITORING"
            verdict_reason = "monitoring_descriptive_only"
            study_stopped = False
    else:
        study_verdict, verdict_reason = verdict(n, n_clusters, delta_exact, interval)
        study_stopped = is_study_stopped(look, study_verdict)

    return {
        "eligible": len(eligible),
        "exposed": exposed,
        "not_evaluable": not_evaluable,
        "arms": arms,
        "n_common_support": n,
        "n_clusters": n_clusters,
        "delta": delta,
        "delta_exact": (None if delta_exact is None
                        else f"{delta_exact.numerator}/{delta_exact.denominator}"),
        "interval": list(interval) if interval is not None else None,
        "discordant": discordant(rows),
        "verdict": study_verdict,
        "verdict_reason": verdict_reason,
        "look": look,
        "study_stopped": study_stopped,
        "secondaries": secondaries(eps),
        "splits": splits(rows),
        "costs": costs(rows),
        "family": FAMILY,
        "budget": BUDGET,
    }
