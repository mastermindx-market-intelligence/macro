# Leadership Rotation — Pre-Registration V2.1 (dated amendment to V1 + V2; verdict mechanics)

**Date of ruling:** 2026-10-14 (UTC). **Authority:** Fable Meta-CEO seat `135304d0`
(LEADERSHIP-ROTATION programme, Chairman masterplan 2026-10-13), scope extension to the
ORCH-REPAIR wave (15:41Z) — items R1, R2, R3 and the T19 F1/F3 ruling.
**Trigger:** the independent T19 challenge lanes found that the V1/V2 verdict machinery
(a) had no class for a voided read, (b) let several distinct failures fall to
`NOT_SUPPORTED` by exhaustion, and (c) left the V1 §5 alarm rules order-dependent.
The harness repair that implements V2 also introduced one gate V2 §3.6 did not
name (§3 below). This document records all of it **before any real-data read**.

**V1 and V2 are not edited.** V1: `research/LEADERSHIP_ROTATION_PREREG_V1.md`, blob
`9d1313e0fc0c5c9720dc1aeb16c9ebf273d70abe` (squash of PR #9251, `68fc4170`).
V2: `research/LEADERSHIP_ROTATION_PREREG_V2.md`, blob
`1fcd151cfc4cdeb321789feb50d3fbb127cce056` (squash of PR #9327, `6e056dc6`).
Every V1/V2 section not named below is carried forward UNCHANGED and incorporated by
reference; where this document and V1/V2 disagree, this document binds from its merge.
Margins, α, Holm m = 6, arms A0–B7/C3, cohort, estimands and partitions are untouched.

**No real-data read has occurred under V1, V2 or V2.1.** P1 development reads: zero
(the committed look ledger `research/LEADERSHIP_ROTATION_LOOK_LEDGER.jsonl` is absent).
P2/P3: zero. All computation so far is P0 synthetic.

---

## §0 Status & identity

| Field | Value |
|---|---|
| Version | V2.1 (amends V1 + V2; both blobs frozen and required unchanged at every reading head) |
| Name | `V2_1` by seat order. It is functionally the amendment that V2 §7 item 9 routes to "a new `..._PREREG_V3.md`"; the name **V3 stays reserved** for the V2 §2 Option A falsifier branch (Option A REJECTED → Holm m = 4) so the two cannot be confused. Every V2 rule that applies to "V3" as *the next amendment* applies to this document. |
| Freeze | at merge of THIS document to `origin/main`; its blob is pinned in the harness as `PREREG_V2_1_BLOB_SHA` (`scripts/leadership_rotation_study.py`) |
| Sealed-read status — P0 | `EXECUTABLE` (synthetic) |
| Sealed-read status — P1 | `DEVELOPMENT` — refused by `run_p1` unless V1, V2 and V2.1 are landed at the reading head AND the committed §3 size-gate artifact passes (§3 below) |
| Sealed-read status — P2 | `NOT_EXECUTABLE` until the five V1 §0 owner acts are complete AND a landed `POWERED_IN_PRINCIPLE` disposition exists per hypothesis (V2 §4; §2 row 4 below) |
| Sealed-read status — P3 | `ACCRUING_NOT_READ`; formation dates from the **first NYSE session after the UTC date this document merges** (V1 §12.7, V2 §7.9 — the reset costs nothing: owner acts 2–5 are unperformed) |

---

## §1 R1 — `VOIDED:<k>` verdict class and invalidators 10–11

V1 §12 already says any invalidator "voids the read; the void is reported". V1/V2 had no
verdict class to report it in. From this merge:

**Verdict classes (complete list, V1 §7 amended):** `VOIDED:<k>` · `NOT_EXECUTABLE` ·
`SOURCE_LIMITED` · `IMMATURE` · `UNDERPOWERED` · `DEVELOPMENT_PASS` / `DEVELOPMENT_FAIL`
(P0/P1 only; never a claim) · `NOT_SUPPORTED` (binding from P2 or P3, preserved) ·
`INSUFFICIENT` (P2/P3, non-binding, no claim — §2) · `CONSISTENT` (P2 pass, no claim) ·
`SUPPORTED` (P3 only).

`VOIDED:<k>` carries the invalidator number `k` (an integer 1–11). It outranks every
other class (§2 row 1). A voided read issues no other class for any hypothesis × group
it touched; the void, its number and its evidence are reported (V1 §13 item 7).

**Invalidators.** V1 §12 items 1–7 and V2 §7 items 8–9 are carried unchanged. Added:

10. Any H1 read (P1, P2 or P3) performed while the V2 §3 re-size record is absent from
    `origin/main`, has any required row not `SIZED` under the two-part rule, or records
    harness blobs that differ from the bytes performing the read. This is the V2 §2/§8
    **mis-size branch**: a mis-sized H1 test does not yield `NOT_SUPPORTED`,
    `UNDERPOWERED` or `DEVELOPMENT_FAIL` — the read is `VOIDED:10`. (The harness refuses
    such a read before loading data, §3; this item covers any read that bypasses it.)
11. Any edit of V2.1 after merge. Amendments are a new dated document with formation
    dates after its own merge (V3 is reserved, §0).

---

## §2 R2 — clause → outcome-class table (first match wins)

Applied per (hypothesis, group) at the read partition. Implemented verbatim as
`verdict()` in `scripts/leadership_rotation_inference.py`; the row order IS the rule.

| # | Condition (V1 §7 clause / source) | Outcome |
|---|---|---|
| 1 | any invalidator `k` fired (§1) | `VOIDED:k` |
| 2 | the statistic cannot be computed as registered (missing arm, empty partition, size gate not passed) | `NOT_EXECUTABLE` |
| 3 | input flagged source-limited (e.g. control C3, rights/coverage of a leg) | `SOURCE_LIMITED` |
| 4 | P2/P3 and the hypothesis lacks a landed V2 §4 `POWERED_IN_PRINCIPLE` disposition | `NOT_EXECUTABLE` |
| 5 | outcomes not yet matured for the read | `IMMATURE` |
| 6 | honest-N < 20 clusters (clause 5) | `UNDERPOWERED` |
| 7 | all-event coverage < 0.80, or undefined (clause 3) | `SOURCE_LIMITED` |
| 8 | P0/P1: margin met (clause 1, incl. H1 non-inferiority sub-clauses) AND Holm-adjusted p < α (clause 1 / V2 §2.3) AND stable (clause 2) AND burden/safety clause holds (clause 4) | `DEVELOPMENT_PASS`; otherwise `DEVELOPMENT_FAIL` |
| 9a | P2/P3: point estimate undefined | `NOT_EXECUTABLE` |
| 9b | P2/P3: margin missed (clause 1 point estimate), or a burden/safety non-inferiority clause failed (clause 4) | `NOT_SUPPORTED` (binding, preserved) |
| 9c | P2/P3: margin met but Holm-adjusted p ≥ α, or unstable (clause 2) | `INSUFFICIENT` (non-binding, no claim) |
| 9d | P2/P3: every clause holds | `CONSISTENT` (P2) / `SUPPORTED` (P3) |

**No failure reaches `NOT_SUPPORTED` by exhaustion.** Under V1 the pass test was a
conjunction and every non-pass at P2/P3 defaulted to `NOT_SUPPORTED`, so too few
clusters, short coverage, or a missing power disposition would have issued a *binding*
negative. Only rows 9b do now: a point estimate that misses its practical margin or a
failed safety clause is evidence against the hypothesis; a margin-meeting estimate that
is not significant or not stable is not, and is `INSUFFICIENT`.

**`INSUFFICIENT` (new).** Non-binding and never a claim. It consumes the look exactly
as any other outcome (V1 §6 look budget unchanged; it creates no extra look). At P3
look 2, or at the single P2 look, it is terminal for that read and is reported as "no
claim". It can never be relabelled `CONSISTENT`/`SUPPORTED` without a fresh registered
look.

**§6 vs §7 reconciliation on P2.** V1 §6 says P2 "can issue `NOT_SUPPORTED` … or
`CONSISTENT`". That row lists P2's *binding* outcome and its pass outcome, not an
exhaustive list: rows 1–7 and 9a/9c of this table apply at P2 exactly as at P3.
`UNDERPOWERED` at P2 is therefore an honest "too few clusters", never converted to
`NOT_SUPPORTED`. The V1 §6 prohibition stands unchanged: P2 can NEVER issue `SUPPORTED`.

**P0/P1 pass set unchanged.** Row 8 passes exactly the combinations V1's conjunction
passed (exhaustively tested over 3,456 combinations in
`tests/test_leadership_rotation_inference.py::test_development_pass_set_is_unchanged_from_v1`);
the only relabel is a coverage-short `DEVELOPMENT_FAIL` → `SOURCE_LIMITED`. No size
count moves.

---

## §3 Ratification of the P1 size-gate reader (amends V2 §3.6)

V2 §3.6 named `assert_prereg_landed` / `assert_protocol_landed` as the enforcement and
said "no new gate machinery". Seat ruling T19 F9 held that protocol landing alone does
not authorise a P1 read. Ratified here as binding: `run_p1` refuses, before reading a
single byte of market data, unless in this order —

1. V1 and V2 are landed at the reading head (`assert_protocol_landed`, unchanged);
2. V2.1 is landed at the reading head with blob `PREREG_V2_1_BLOB_SHA` (`assert_prereg_landed`);
3. the committed artifact `research/LEADERSHIP_ROTATION_STUDY_T12R_2026-10-14.size_gate.json`
   passes `assert_size_gate_passed`: rule `V2_SEC3_TWO_PART`, α = 0.025, `sized` true; all
   seven rows (H1–H3 × 2 groups + family-any) present for each required δ = 0 cell
   {0, 1, 2, 3, 4, 48}; every row ran M ≥ 400 OK sims and is `SIZED` by both recorded parts
   AND by recomputation from its own counts; H1 null method `V2_OPTION_A` with K ≥ 1,000;
   the V1/V2/V2.1 blob pins match; the recorded harness blobs match both the reading
   commit and the runtime bytes;
4. the committed look ledger is readable (an unreadable ledger fails closed); the read is
   recorded as look `prior + 1`.

A refusal is a closed-vocabulary `SIZE_GATE_*` reason. This adds no new criterion beyond
V2 §2–§3; it is the mechanical form of "re-size landed and green (§6)".

---

## §4 R3 — alarm classification as a first-match ordering (amends V1 §5)

V1 §5 lists four alarm rules whose scopes overlap ("outside every `[T, T+40]` window"
also covers an alarm inside an up-phase after `T+40`). Binding order, per kept alarm `a`
in time order, over QUALIFYING phases only (each with onset `T` and up-leg end `P`):

| # | Condition | Class |
|---|---|---|
| 1 | `a` lies in some qualifying up-leg `[T, P]` (the first such phase is the host) and `a ≤ T + 40`, and the host's match is not yet taken | `MATCHED` (delay `a − T`) |
| 2 | as row 1 but the host's match is already taken | `REPEATED` |
| 3 | `a` lies in a host up-leg with `a > T + 40`, and the host already holds a `MATCHED` or `LATE` alarm | `REPEATED` |
| 4 | `a` lies in a host up-leg with `a > T + 40`, host not yet engaged | `LATE` |
| 5 | otherwise (in no qualifying up-leg) | `FALSE_START` (subtype `EXPIRES` / `PERSISTENT` / `NONE`, V1 §5) |

Equivalently: inside a qualifying `[T, P]` the first alarm is `MATCHED` (delay ≤ 40) or
`LATE`, and every later alarm in that phase is `REPEATED`; `LATE` outranks `FALSE_START`.
Onsets with no `MATCHED` alarm are `MISSES` (unchanged). This is the ordering the T11
harness already implements (`classify_alarms`, ORCH-SCI ruling R7); it is pinned by
`tests/test_leadership_rotation_episodes.py::test_r3_*` against an independent oracle.

---

## §5 Ruling on T19 F1, F2, F3

- **F1** (the Wilson-lower-bound gate is not authorised by V1 and tolerates 5.00 % at
  n = 100 and 7.14 % at n = 42): **settled by V2 §3.** The two-part rule adds the point
  envelope `α + 2·sqrt(α(1−α)/M)` and M ≥ 400; at M = 400 the largest SIZED count is
  16/400 = 4.00 % (17/400 fails both parts). **Residual carried here:** M is each row's
  OWN count of OK δ = 0 sims (unreached/failed sims never count); a row with M < 400 is
  `SIZE_NOT_EXECUTABLE`, never SIZED.
- **F2** (a row with zero OK sims): `SIZE_NOT_EXECUTABLE`; the gate is not passed.
- **F3** (R13 is an amendment, not a reading of V1 §7): **settled by V2 §5**, which
  *replaces* the V1 §7 H3 overlap sentence and is listed in V2 §1 as a change. R13
  binds from V2's merge; no claim is made that V1 meant it, and no read under V1
  occurred.

---

## §6 Option A precision (completes V2 §2; binding for every H1 null)

1. Formation-window moments: `ΔR` uses sessions `t ∈ (s0, end]` with both endpoints
   finite; σ̂ with ddof = 1; ρ̂ = median of the pairwise-complete Pearson correlations of
   the group's pairs (≥ 2 pairs). No `Y_h` of any horizon enters (V2 §7.8).
2. Matching grid: σ_b = σ̂ rounded to 0.0005; ρ_gen = (ρ̂·σ_b² − 9e-6)/(σ_b² − 9e-6)
   clipped to [0, 0.95] and rounded to 0.05 (9e-6 = the G1 market variance). σ̂ or ρ̂
   unmeasured (< 2 measured pairs), or σ_b² ≤ 9e-6 → the null is `NOT_EXECUTABLE`, its p
   is forced to 1, and the H1 class is `NOT_EXECUTABLE` (§2 row 2) — never a scored fail.
3. Each null path is G1 at δ = 0 with the matched (σ_b, ρ_gen), generated from index 0
   with the window opening at the 252-session warm-up. It is evaluated at `e*_N`, the
   first index at which its honest-N ≥ the observed N; the realised N is recorded.
   (Honest-N is non-monotone, so this first-reach rule differs, disclosed, from the P0
   bisection.)
4. A null path that never reaches N within 96 years, or whose statistic is undefined,
   counts as ≥ the observed statistic (conservative). An undefined observed statistic
   gives p = 1.
5. Alarm EXPIRES/PERSISTENT subtyping is not used on null paths (`off_index = None`).
6. p = (1 + #{null ≥ obs}) / (1 + K) per condition; H1 p = max(p_a, p_b); reported
   quantile = `np.quantile(finite nulls, 0.975)`.
7. Streams: null seed = 20261014 + crc32(`partition|group`), path j =
   `SeedSequence(entropy=seed, spawn_key=(j,))`, drawn in 252-row chunks (prefix-
   invariant); P0 size paths use `SeedSequence([20261014, cell, k])`. The two stream
   families are disjoint (pinned by `tests/test_leadership_rotation_null.py`). One
   K-path bank per (partition, group, pair count, σ_b, ρ_gen, block of 8 consecutive N)
   is shared by every read at that key; it never serves as a size path (V2 §7.8).

**Limitation (carried from V2 §2.4):** the null is parametric (Gaussian G1 at matched
moments). A real series with fatter tails or regime-dependent ρ may be mis-sized
relative to it; the V2 §3 re-size bounds this only for the registered P0 cells.

---

## §7 Change log

- 2026-10-14 — V2.1 created under the seat's 15:41Z scope extension. Implemented in the
  same PR as the V2 harness repair (`claude/lr-harness-repair-2026-10-14`):
  `verdict()` R2 table, `classify_alarms` R3 tests, `run_p1` gate (§3), look ledger.
- Alternatives rejected: (a) mapping every non-pass to `NOT_SUPPORTED` (V1 default) —
  makes "too few clusters" a binding negative; (b) a separate `NOT_POWERED` class for
  row 4 — `NOT_EXECUTABLE` already means "cannot be performed as registered", and V2 §4.3
  names it; (c) naming this document V3 — collides with the V2 §2 falsifier branch.
- Reversibility: a further dated document only; never an edit of V1, V2 or V2.1.
