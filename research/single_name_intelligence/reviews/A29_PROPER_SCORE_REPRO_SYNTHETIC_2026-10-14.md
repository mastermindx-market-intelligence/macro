# A29 — Proper-score reproduction against frozen SNI baselines (synthetic)

Lane: A29B
Date: 2026-10-14
Branch: claude/sni-a29b-20261014-20261014T052450Z
Head: see `git log --oneline -1` on the lane branch.

## Status of the acceptance row

> not forecast support; no frozen SNI baseline exists (R1-gated); row stays PARTIAL

(A29 — "Proper scores and coverage reproduce against frozen baselines" remains
PARTIAL after this lane. The lane produces an exact-arithmetic reproduction
of the ledger's Brier score over seeded synthetic data; the missing piece is
a frozen SNI forecast baseline. Owner wiring is R1-gated and is held by a
Chairman ruling the seat does not hold.)


## What this lane proves

- The ledger's mean-squared-error computation (`brier()`) over only the
  MATURED forecasts of a family **agrees exactly** (max |diff| <= 1e-12)
  with an independent reference implementation that uses
  `fractions.Fraction` arithmetic on the same `(p, outcome)` pair set.
- The agreement holds across 200 synthetic ledgers covering 361 families
  and 2849 (p, outcome) pairs, with p drawn from `{0.05, 0.10, …, 0.95}`
  plus random floats in (0, 1), and outcome ∈ {0, 1}.
- The agreement holds whether resolution is MATURED, UNPRICEABLE,
  CENSORED, left unresolved (PENDING), or replaced by ABSTAIN; only
  MATURED forecasts enter the reference set.
- A family with zero MATURED forecasts raises
  `LedgerRefused(NO_MATURED_FORECASTS, family_id)` — the reference is
  not called. The reason string matches the ledger's refusal reason
  exactly.
- Replay parity: a ledger reloaded from disk through `EvalLedger(path)`
  (or via the explicit `replay(path)` public surface) reproduces the
  same Brier per family as the original, exactly (no float drift).
- The reference function is a strictly proper scoring rule under
  Bernoulli(q): for each q ∈ {0.1, 0.3, 0.5, 0.7, 0.9}, the
  exactly-computed expected Brier `E_o~Bernoulli(q) [(p - o)^2]`
  over a 101-point p-grid is minimised at `p == q` (strictly smaller
  than at every other grid point). This is the properness sanity of
  the reference — not a forecast or signal of any kind.


## What this lane does NOT prove

- It does not reproduce an SNI forecast against a frozen SNI baseline,
  because no frozen SNI baseline exists. (R1-gated.)
- It is not forecast support. It is arithmetic reproduction of the
  ledger's Brier computation over synthetic data.
- The hit/return grading in `residual/` and `event_response/` is not
  probabilistic forecast support until an accepted bridge exists; that
  is out of scope here.
- The reference is descriptive. It is never causal. It is never
  "news impact". It is not a forecast, signal, ranker, gate, sizer,
  escalation, or trade authority. Authority flags stay literal False
  everywhere this lane writes them.


## Frozen facts

- Seed: `SEED = 20261015`
- Random source: `random.Random(SEED)`
- Ledger count: `N_LEDGERS = 200`
- Familes tested for agreement (with >= 1 MATURED forecast): 361
- Total matured `(p, outcome)` pairs compared: 2849
- Max |brier(ledger, fam) - float(reference(pairs))| over all families: 1.110e-16
  (re-run; expect ULP-level float rounding noise on the order of 1e-16 to 1e-12.


## Method (deterministic, exact)

- `_ref_brier(pairs)` — pure function. `Fraction(p)` (exact binary value
  for float inputs), `Fraction(o)` for int {0, 1} outcomes. Mean
  = sum((Fraction(p) - Fraction(o))**2) / N, all in Fraction arithmetic.
- The ledger's `brier(ledger, family_id)` uses `math.fsum` and division
  by `len(pairs)`. Floats inside the ledger are passed through
  `float(p)` and `float(outcome)`.
- Each test sets up both sides from the same JSONL file. The reference
  walks rows directly (does not call `_brier_pairs`); the ledger's
  `brier()` does call its private `_brier_pairs`. This independence is
  what the agreement test is verifying.
- Excluded pairs:
  - `state = UNPRICEABLE` — excluded by `_brier_pairs` AND by reference
    (constructed families confirm: adding an UNPRICEABLE forecast does
    not change either brier).
  - `state = CENSORED` — same.
  - `state = PENDING` (no RESOLVE row) — same.
  - `ABSTAIN` instead of PUBLISH — same.


## Refusal parity

- `NO_MATURED_FORECASTS` is raised when the family has zero MATURED
  forecasts (verified for an ABSTAIN-only family, a mixed-PENDING-only
  family, and a zero-forecast family). The reference function is never
  called for those families. Error code matches
  `REFUSAL_CODES ⊇ {"NO_MATURED_FORECASTS"}` and
  `LedgerRefused.code == "NO_MATURED_FORECASTS"`.


## Replay parity

- For each sampled family, a reloaded `EvalLedger(path)` reproduces
  the same Brier exactly (no drift). `replay(path)` returns the same
  state fingerprint as `EvalLedger(path).state()`.


## Properness sanity of the reference

For each q ∈ {0.1, 0.3, 0.5, 0.7, 0.9}, on a 101-point grid
p ∈ {0.00, 0.01, …, 1.00}, the exact expected Brier
E_o~Bernoulli(q) [(p - o)^2] = (p - q)^2 + q(1 - q)
computed via the same reference-arithmetic machinery is strictly
smaller at p == q than at every other p in the grid. The reference
is a strictly proper scoring rule; this confirms the analytic shape,
not the ledger's forecasts (there are no forecasts here).


## Perturbation proof

A monkeypatch of `sni_eval_ledger._brier_pairs` that drops the last
MATURED pair makes the agreement test fail. The pre-monkeypatch
sanity check holds; the post-monkeypatch agreement assertion fails
with a non-trivial `|diff|` exceeding 1e-12. The perturbation is
test-local (pytest `monkeypatch.setattr`), is never committed, and is
not retained outside the test function.

FAILED_LINE emitted by the perturbation test (concrete, captured from the
run that produced 2 MATURED forecasts `[(0.5, 1), (0.1, 0)]`):
  FAILED assertions: agreement broken after _brier_pairs perturbation
  (last pair dropped): |brier - ref| = 1.200000e-01 > 1e-12


## Authority flags

Every authority flag stays literal `False` in every payload this lane
writes. Nested dicts and list elements carrying any of
`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority`, `trade_authority` are refused by the ledger
(`AUTHORITY_FLAG_REFUSED`), and the test suite asserts no flag is true
in the import surface. This lane does not feed a ranker, gate, sizer,
signal, escalation, or trade path. Authority flags remain False across
all generated ledgers.


## Owners (this lane CONSUMES, never re-implements)

- `engine/qledger.py register / grade_claim`
- `engine/grading_stats.py brier_decomposition`
- `engine/trial_ledger.py TrialLedger._append_rows`
- Data OS identity, Stock Identity, Company Event/Earnings, FIF,
  Capital Structure, Options, Research Vault.

This review is an SNI-local DRAFT contract. It is not Evaluation OS.
It does not write qledger. It does not cut a seal.


## Test functions

19 test functions in `tests/test_sni_a29_proper_score_repro.py`,
each named `test_a29_<slug>`.
