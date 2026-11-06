---
key: FDA-SWEEP-COMPARED-A-DEDUPED-COUNT-TO-A-RAW-TOTAL
claim: >-
  The openFDA shortages sweep could never qualify a generation, because its completeness
  test compared the POST-deduplication unique_count against the source's RAW reported_total.
  Measured live 2026-09-28: the endpoint reported total=1601 while four
  (package_ndc, initial_posting_date) pairs appeared twice, capping unique_count at 1597, so
  the loop's only success exit (unique_count >= reported_total) never fired; the sweep paged
  past the end of the feed, openFDA answered skip >= total with HTTP 404, raise_for_status
  raised, and the sweep recorded failure_code=PAGE_FAILED / qualified=false. That drove
  summarize_supply to _UNAVAILABLE and served "FDA source unavailable" to every user. One
  duplicate key anywhere in the feed was sufficient; the feed had four.
falsifier: >-
  Run `python3 -m pytest tests/test_fda_sweep_duplicate_key_completeness.py -q` — it asserts
  a feed whose reported_total exceeds its distinct (package_ndc, initial_posting_date) count
  still qualifies, and that a genuinely short feed does not. Refuted if completeness is ever
  again computed from a deduplicated count at collectors/fda_shortages.py:241, or if the
  loop exit at collectors/fda_shortages.py:230 reverts to unique_count.
so_what: >-
  The public seam was correctly refusing a feed that was never broken, so every
  instrument downstream read as working-as-designed and the defect was invisible from the
  consumer side. Completeness is a RAW-row question ("did we observe every record the
  source reported"); deduplication governs what is STORED and must never be able to make a
  complete interval look truncated. Any collector that dedupes while paging against a
  source-reported total carries this same bug shape — check the exit condition's operand.
kind: landmine
verified_at: 2026-09-28
verified_by: >-
  `python3 -m pytest tests/test_fda_sweep_duplicate_key_completeness.py
  tests/test_fda_shortages_generation.py tests/test_fda_supply_probes_mixed.py -q`
  (78 passed across the FDA/scarcity suites); live sweep receipt in #PR body
scope: macro
confidence: verified
---

## How it presented

The served healthcare chip read `FDA source unavailable — no qualified generation on file,
refresh failed` and was adjudicated CORRECT (`R-D1-FALS-01`) — which it was: with
`qualified: false`, `summarize_supply` reaches `_UNAVAILABLE` at `engine/fda_scarcity.py:243`
and `_label` selects exactly that leaf. The seam performed the refusal it was built to
perform. **The refusal was right and the input was wrong**, and nothing on the consumer side
could distinguish that from a genuine upstream outage.

Two properties hid it further:

- **The drip is non-fatal by design.** `scripts/build_foresight.py` wraps the refresh in
  `try/except … log.warning("fda_shortages drip failed (non-fatal)")`, and `RENDER_NO_DRIP=1`
  skips it entirely, so a green `daily.yml` is not evidence the drip ran, let alone succeeded.
- **`partial_rows_observed` is uninformative on failure.** `collectors/fda_shortages.py:257`
  returns `[] if failure_code else list(rows_by_key.values())`, so `rows` is emptied by
  construction on ANY failure. A prior reading of `partial_rows_observed: 0` as "page 1
  yielded nothing" was wrong; `PAGE_FAILED` only ever means `pages >= 1`.

## Why no test caught it

Every pre-existing fixture used a feed where `raw_count == unique_count` (typically 1 == 1),
so none could reach the branch. `REPEATED_PAGE` covers an identical *page identity*, never
two distinct rows on different pages sharing a dedupe key. This is a second instance of
`DSC:A-SYNTHETIC-FIXTURES-NEVER-REACHED-THE-BRANCH-THE-LIVE-FEED-TAKES` in the same
collector family — there, a MIXED branch the live feed takes had no fixture; here, a
duplicate key the live feed carries had no fixture.

## The fix

Both the loop exit and `complete` now compare `raw_count` against `reported_total`.
Deduplication still governs stored rows (1597 of 1601 live). Pinned by
`tests/test_fda_sweep_duplicate_key_completeness.py`, whose two falsifier probes assert a
genuinely truncated feed (reports 6 / 10, serves 4 / 3) still refuses to qualify — so the
change corrects the check rather than deleting it.

## Live proof

`collect_shortage_sweep(_fetch_page, …)` against the real endpoint post-fix:
`qualified: True`, `failure_code: None`, `raw_count: 1601`, `unique_count: 1597`,
`reported_total: 1601`, `complete: True`, `pages: 17`, `source_generation: 2026-09-26`.
`summarize_supply` then yields `MIXED_REPORTED` with counts
`current 1149 / resolved 7 / discontinued 441` and the label
`FDA: mixed — current 1149 / resolved 7 / discontinued 441 · captured 0 d ago · source
generation 2026-09-26` — lawful under the D1 vocabulary (all non-zero components enumerated,
discontinuation never reported as resolution, no banned substring, ZH parity present).

## Known source-data characteristic (deliberately NOT patched)

openFDA itself serves two malformed `availability` tokens: lowercase `unavailable` (x1,
case-normalizes correctly) and misspelled `Unvailable` (x1, normalizes to `unknown`). One
row of 1597, failing SAFE to an honest `unknown` rather than a wrong assertion. Adding
spelling-correction aliases to a normalizer would be speculative repair against a source
that may fix its own typo; recorded so a successor does not re-discover it as a defect.
