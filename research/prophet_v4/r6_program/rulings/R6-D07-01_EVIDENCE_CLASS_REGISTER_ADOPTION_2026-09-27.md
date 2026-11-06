# R6-D07-01 — Evidence-class register: adoption ruling (2026-09-27)

Seat: Fable Meta-CEO 48cdfd56 (Prophet US R6 program, carrier #6805 scientific / #7856 records).
Scope: the D07 draft register `wave3/D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md` +
`wave3/d07_evidence_class_register_draft.json` (31 rows, SOURCE_SHA `cde1e7e5`, content head `a60c890c`,
base-refreshed at `84430af8`). This ruling changes no runtime evidence value and promotes nothing.

## 1. Question
Does the seat adopt the draft as the R6 evidence-class register v1, and what does that resolve for D07?

## 2. Ruling
**ADOPTED as register v1.** The classing rule in the draft (§Classing rule: `OBSERVED_AS_RUN`,
`PUBLIC_INFO_REPLAY`, `RETROSPECTIVE`, `null` + closed `null_reason`; flag vocabulary `TESTED | STATED | ABSENT | N/A`)
is binding across the R6 program from this ruling forward. The histogram 0 / 4 / 5 / 22 is the honest current state and
is recorded as such — 22 nulls are blockers with named remedies, not defects of the register.

D07 is **resolved at the vocabulary level**: consumers may now carry `evidence_class` (+ `null_reason`) on the rows this
register names, using only these words. D07 is **not resolved at the row level**: each null row stays blocked for its
consumer until the row's `prospective_remedy` lands with a receipt that satisfies the classing rule at a named sha.

## 3. Binding rules (from the review amendments F1–F11, now law)
1. A class may be raised only by a receipt satisfying the classing rule at a named SOURCE_SHA; never by assertion, never
   by a consumer. `OBSERVED_AS_RUN` requires a writer-stamped capture clock and a pinned store generation (F1).
2. A known construction with an unprovable knowledge boundary is `RETROSPECTIVE`; an absent or unidentified element is
   `null` (F3). A model of unknown vintage in the path caps the row at `RETROSPECTIVE` (F2).
3. `UNBLOCKED_UNDER_CLASS RETROSPECTIVE` (today: B11 only) permits display-tier / diagnostic use under that label and is
   never a promotion, rank, size, or authority claim — the gauntlet law is unchanged.
4. Leakage flags are `TESTED` only with a `tests/` receipt; a code statement is `STATED`; non-use is `ABSENT` (F5).
5. Family-specific cells only; a never-acquired family carries `N/A — not acquired` and `NOT_ACQUIRED` (F6).
6. Every register change is a new PR citing `R6-D07-01`; the JSON and the markdown move together; SOURCE_SHA is
   re-pinned whenever a cited file changes.

## 4. Consumer dispositions (binding until superseded)
| consumer | rows | disposition | remedy owner |
|---|---|---|---|
| B04-D | S1 ×14 | BLOCKED | B04-D (per-family identity/route/capture/correction) |
| B08 | S2 ×4 | BLOCKED | B08 (SEC event-set reconstruction, source-release routes, frozen prospective model) |
| B10 | S3 ×2 | BLOCKED | B10 (pinned episode generation + write-time `recorded_at`) |
| B11 | S4 ×3 | UNBLOCKED_UNDER_CLASS RETROSPECTIVE | — (display-tier only) |
| B15 | S5 ×2 | BLOCKED | B15 (vendor model identity + prospective capture) |
| B18 | S6 ×3 | BLOCKED | B18 (dated membership, failure-inclusive universe) |

## 5. Evidence
- Lane review glm-codex/glm-5.3 PASS at `8c0fad84` → `a60c890c` (`ext/lanes/pu_w3_d07_register_v2/r2_review.out.md`).
- Seat-commissioned Opus read-only review `reviews/RV_7856_D07_REGISTER_OPUS_2026-09-24.md`: "RULING MAY PROCEED:
  YES WITH AMENDMENTS" — all eleven findings applied in the v2 draft (PR body §Latest review repairs).
- Independent Opus read-only audit 2026-09-27 (~23:20Z): content PASS plausible; the only red was inherited from the
  base (`options-payoff-lab-consumer` paths, healed on main at `386c98ed`); base refreshed at `84430af8`.

## 6. Alternatives rejected
- Hold adoption until any row reaches `OBSERVED_AS_RUN`: rejected — the register's value is the honest null map; waiting
  would keep six consumers without a vocabulary for nothing gained.
- Adopt with a softer null→RETROSPECTIVE rule for recorded-clock rows: rejected (F3) — it would launder absence as a
  known construction.

## 7. Reversibility
Superseded only by an `R6-D07-02` ruling on new evidence (a landed remedy, a refuted receipt, or a Sol/Chairman reversal).
