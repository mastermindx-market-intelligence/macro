---
workstream: WS:GMI-THEME-GRAPH
session: claude/sector-cycle-cap-coverage-20260917-sol
model: sol
ended_because: ci_handoff
mission: >
  Heal the existing capitalization reference owner so house-theme members are not
  excluded from cap lookup merely because they lack GICS labels, while preserving
  R9's null-honest cap admission and all existing data/publication authorities.
state_before: >
  R8 found 500/702 positive exact-key cap matches and 198 P1 keys absent from the
  reference cache. R9 admitted all 49 house groups for non-cap representations but
  kept cap-sized views unavailable. The provider had not been shown to lack the
  missing names.
changed:
  - path: scripts/build_polygon_universe.py
    what: >
      PR #7278 changes only the existing cap owner's target selection: cap lookup
      targets are the union of GICS-labelled tickers and active members from the
      existing house basket membership owner. Missing GICS stays null; provider,
      checkpoint, freshness, regression guard and atomic cache write remain unchanged.
  - path: tests/test_build_polygon_universe.py
    what: >
      Adds a build-level regression proving an active theme-only member reaches the
      cap fetcher without receiving invented GICS, while a removed member stays out.
verified:
  - claim: >
      The 198 P1 keys absent from the cap reference are exactly the 198 P1 keys
      excluded by the old GICS-derived fetch universe.
    command: >
      Compare frozen P1 member union, current breadth plus us_sector GICS union and
      R8 reference.parquet at Macro c3d4b81; test set equality of absent-cap and
      outside-GICS keys.
    result: >
      P1=702, GICS/reference=506, P1 in GICS=504, P1 outside GICS=198,
      P1 absent cap rows=198, and the two 198-key sets are equal. All five zero-cap
      themes have every member outside the old fetch universe.
  - claim: The repair has a discriminating red-green regression.
    command: >
      python3 -m pytest -q
      tests/test_build_polygon_universe.py::test_build_fetches_cap_for_active_house_member_without_gics
    result: >
      Before implementation failed because fetched={AAPL} instead of {AAPL,RKLB};
      after implementation passed.
  - claim: The existing cap-owner suite passes on the repaired source.
    command: python3 -m pytest -q tests/test_build_polygon_universe.py --tb=short
    result: 39 passed, 8 skipped; compileall and git diff --check also pass.
  - claim: >
      The repaired target selector covers the full current house catalogue without
      becoming a broad-market crawler.
    command: >
      Run _load_house_basket_tickers against exact current membership and compare
      with the existing 506-row reference, without provider calls or cache writes.
    result: >
      702 active house members; 198 new house-only targets; target union 704
      (702 house plus two GICS-only names); all pass the existing US-like symbol gate.
  - claim: >
      The provider-coverage probe respected the credential boundary and made no
      alternate secret attempt.
    command: >
      Attempt read-only _fetch_mcap qualification for the 198 new targets only after
      _polygon_key() check, with no cache/source write.
    result: >
      Stopped immediately: no POLYGON_API_KEY/MASSIVE_API_KEY in this execution
      context. No provider coverage result is claimed.
unverified:
  - claim: Provider returns positive market cap for the 198 newly admitted targets.
    what_would_verify: >
      Existing nightly/credentialed owner runs #7278 after release and records
      target/positive/missing coverage without exposing secrets or raw values.
  - claim: Full repository CI is green for PR #7278.
    what_would_verify: >
      Existing hosted CI 35296477174 concludes on exact head
      504a55cc99d145fb36c71466a2d6be44276ab720. Local sparse execution is not a
      substitute.
  - claim: Cap-sized Atlas is admitted.
    what_would_verify: >
      Post-release cap coverage/clocks/identity are qualified under R9 and the
      eventual consumer passes its own semantic/browser acceptance.
unresolved:
  - >
    PR #7278 hosted CI is running: fences and parent ci-authority succeeded; ci-plan
    and contract-delta were in progress at 2026-09-18T01:45Z. One
    ci-authority/codex/merge-queue-pilot subcheck showed FAILURE while the parent
    workflow concluded SUCCESS; its job log was unavailable by GitHub API/gh and
    the cause is not inferred.
  - >
    Local broader CI-pack execution is incomplete because this sparse worktree omits
    data/. The only observed reds were data-dependent tests; they are not claimed
    repaired or green.
  - >
    #7252 and #7211 remain separately queued under existing #6351 executor starvation;
    #7278 does not become their dependency or replace their release gates.
  - >
    R9 still forbids cap-sized representations until actual post-repair coverage,
    clock and identity semantics are accepted.
next_actions:
  - >
    Consume #7278's existing hosted CI through its normal return path; do not rerun,
    cancel or create another runner.
  - >
    If exact-head hosted source proof is green, perform bounded independent source
    review/release adjudication on #7278 without widening to Atlas UI.
  - >
    After release, use the existing credentialed nightly owner to measure recovered
    cap coverage and keep missing/nonpositive values null.
  - >
    Feed accepted coverage back into the R9 cap-admission gate; do not change the
    first Atlas population or product ambition merely because some caps remain absent.
do_not_redo:
  - R1-R9 Finviz/Atlas research, R8 missing-cap census and R9 rights-safe scope ruling.
  - >
    Reinvestigating whether the 198 missing cap rows are caused by GICS target
    selection; the set equality is established.
  - >
    Creating another Polygon fetcher, cap cache, checkpoint, scheduler, identity
    resolver or publication plane.
  - >
    Re-running the provider probe without a lawful credential context or treating
    credential absence as provider coverage failure.
danger_areas:
  - >
    Expanding cap lookup must not invent GICS; market cap and GICS are independent
    optional fields.
  - >
    A provider 404/null remains unavailable, not zero and not a tiny rendered bubble.
  - >
    #7278 is an input-coverage repair, not cap-sized Atlas acceptance or full
    lower-cap parity.
  - >
    Sparse-worktree data-dependent reds must not be 'fixed' as product regressions;
    hosted full-checkout CI is the relevant release proof.
prs: [7278, 7234, 7252, 7211]
---

## Current carrier

Source carrier: Macro PR #7278, branch
`claude/sector-cycle-cap-coverage-20260917-sol`, exact semantic head
`504a55cc99d145fb36c71466a2d6be44276ab720`.

Research/continuity carrier remains #7234. P1 #7252 and publication #7211 are
unchanged. This handoff records source and test effects already published on #7278;
it authorizes no duplicate source edit, CI rerun, provider credential acquisition or
Atlas implementation.
