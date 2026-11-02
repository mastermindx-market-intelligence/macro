# Seat adjudication — independent review R1 (Healthcare D1 + whole package)

Operation `gmi-healthcare-fable-ceo-e2e-20260924-chairman-001` · adjudicator: Healthcare Fable CEO seat (Claude Fable 5.1 session `1172846f`) · 2026-09-24 ~10:40Z.

**Review consumed:** `HC_INDEPENDENT_REVIEW_R1_2026-09-24.md` (Claude Opus reviewer child of this session, read-only, non-author; independence limitation: same account family as the seat — organizational independence from the plan author, not institutional independence from the program). Exact inputs: frozen corpus `e5789583`, plan blob `23cd3788`, handoff blob `452aba8e`, R11 `5dde2a37`, R12 `94c4d991`, R7 `cb08945f`. No #7870 bytes read → shared-compatibility acceptance is NOT covered by this review and stays with #7870's owner.

**Companion artifact:** frozen acceptance probe suite `tests/test_fda_supply_probes.py` (second Opus reviewer child; 14 tests for R8-A18…A27, R9-A02, R9-A07, R10-A07, R10-A11; `14 failed` on `origin/main` `83223aa5`), committed RED as the first commit of carrier PR #7930 (`6a929f59`). Build lanes may not edit it.

## D1 verdict: REQUEST_CHANGES → adjudicated as bounded seat rulings; D1 UNLOCKED for implementation

The review found no defect in the plan's D1 direction or in R7's root-cause analysis; every blocker is a defect in the interface contract the seat had frozen on top of the plan, repairable inside D1's own files. Dispositions (review IDs → binding rulings in `SEAT_RULINGS_T0{1,2}_R1_2026-09-24.md`):

| Review | Disposition | Ruling |
|---|---|---|
| F-D1-01 / R-D1-01 chip invisible for band NONE | ACCEPTED | R-T01-02, R-T01-16: visibility keys on `source_status`; all seven statuses render |
| F-D1-02 / R-D1-02 tier moves with chip presence | ACCEPTED (composition follows configuration) | R-T01-10: `compute_fda_scarcity` never returns None for a configured theme; UNAVAILABLE row → chip → tier unchanged by outage |
| F-D1-03 / R-D1-03, R-D1-04 no capture channel; stale fallback unmarked | ACCEPTED (R-D1-03 partially: bare-frame path stays row-derived but capture-unknown by construction) | R-T02-17 `df.attrs["fda_observation"]`; R-T01-11 |
| F-D1-04 / R-D1-05 invented age limit | ACCEPTED | R-T01-12: `max_capture_age` optional, `stale=None` by default, facts reported |
| F-D1-05a / R-D1-08 nightly `git add data/` second writer | ACCEPTED as declared limitation (no daily.yml change in D1) | R-T02-13 |
| F-D1-05b / R-D1-06 two renames | ACCEPTED in adapted form (parquet-then-sidecar with `parquet_sha256` verification; probe contract preserved) | R-T02-11 |
| F-D1-05c / R-D1-07 generation regression | ACCEPTED | R-T02-12 (`GENERATION_REGRESSION`, after the predecessor check) |
| F-D1-06 / R-D1-09 no CI carrier | ACCEPTED | packet §(7): job `healthcare-fda-supply`, `run:`+`paths:` in one diff |
| F-D1-07 / R-D1-10 dedupe key vs history; cap | ACCEPTED (current rows + absence/status-change metadata; cap in generations = 90) | R-T02-14 |
| F-D1-08 / R-D1-11 flat enum hides unclassified remainder | ACCEPTED as coverage-in-label (plan enum retained) | R-T01-13 |
| F-D1-09 / R-D1-12 ban scoped to label only | ACCEPTED (rationale/label_zh/details/HTML; adds "demand exceeds supply", "supply constraint lifted") | R-T01-14 |
| F-D1-10 / R-D1-13 `label_zh` has no consumer | ACCEPTED (one-hunk template edit in T01) | R-T01-15 |
| F-D1-11 / R-D1-14 `fetched_utc` as clock | ACCEPTED | R-T02-15 |
| F-D1-12, F-D1-13 / R-D1-15 cap constant; keyless collision | ACCEPTED | R-T02-16 |
| Probe author GAP: A20 chip invisibility | RATIFIED as R-T01-02 (visible) | — |
| Probe author GAP: "tell" substring bans "intelligence" | ACCEPTED as-is (labels avoid the substring) | R-T02-07, R-T01-04 |

Verified-and-no-finding retained: the FDA chip cannot move `stage`/`entry` (glut band comes from `engine.glut_watch`).

## Whole-package verdict: HOLD (scoped to D2–D4) → CONSUMED, does not block D1

Unresolved decision named by the review: which #7870 head / contract bytes D2–D4 are reviewed against (three circulating pins; foundation unlanded). Disposition: D2–D4 review is deferred until #7870 lands on `main` and a single accepted pin exists; the seat will re-commission a scoped review then. F-PKG-01 (R11 §4 declared plan blob `f58970d6` ≠ shipped `23cd3788`) is explained by R13's consolidation after R11 was written (#7788 comment 5809979462 names the new blob) — recorded, not a defect in the operative plan. F-PKG-03 (R8-A40 D1→D3 coherence has no test) is carried to D3.

## Remaining D1 gates (unchanged by this adjudication)

Exact-head independent review of the implementation PR (Opus red-team, read-only) before merge; hosted CI incl. the new job green; source rights for openFDA display retained as the existing public-domain posture (no new source family); live proof = nightly drip receipt + rendered foresight chip on the deployed site. All 60 application requirements remain NOT_EXECUTED until those receipts exist.
