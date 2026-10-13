---
workstream: "WS:PROPHET-NEWS-IMPACT"
session: "claude/prophet-ni-phase1-integration-20261012"
model: opus
ended_because: complete
decisions: ["DEC:NEWS-IMPACT-PHASE1-VALIDATOR-SEMANTICS"]
mission: >
  Phase 1 wave w1 of the Prophet news-to-business-impact masterplan: build the leaf
  package engine/news_impact/ (validator, benchmark sampler, cluster bridge, issuer
  resolver) against the byte-frozen v1 contract, close every schema-only gap the hostile
  corpus found, and land the accepted wave-2 design packets A1-A7 plus the C2/C3 census
  so the next wave builds from frozen specs. Labor ran on seat-launched Grok and GLM
  lanes (ext/remote_sub.sh, ubuntu0/ubuntu1/ubuntu2); no native Claude children.
state_before: >
  origin/main c7543cd1 held the frozen contract (PR #8873) and the masterplan (#8777) but
  no engine/news_impact/ package, no sample manifest schema, no hostile fixtures and no
  Phase 1 designs. The ubuntu0/ubuntu2 lane clones have empty working trees, so build
  lanes read owner source from a read-only R/wtx extract (ubuntu0 at da8b1133, ubuntu1 and
  ubuntu2 at c7543cd1) through R/in/common/harness_overlay.sh.
changed:
  - path: engine/news_impact/validate.py
    what: >
      Contract validator: closed REASON_CODES, R1/R2 display projection, R4 closed locators,
      the S1-S13 semantic layer (DEC:NEWS-IMPACT-PHASE1-VALIDATOR-SEMANTICS), load_strict
      (duplicate keys and non-finite constants) and validate_text; CLI parses strictly.
  - path: engine/news_impact/sampler.py
    what: Deterministic 200/200/200 benchmark candidate sampler writing sample_manifest.v1 rows.
  - path: engine/news_impact/cluster.py
    what: Bridge from the existing qbus news cluster owner to ev2_ cluster ids; no second clusterer.
  - path: engine/news_impact/issuer.py
    what: Issuer resolution over existing owners; unresolved issuers stay explicit, never guessed.
  - path: contracts/news_impact/sample_manifest.v1.schema.json
    what: NEW closed schema for sampler output rows.
  - path: tests/test_news_impact_validate.py
    what: 88 tests (63 kept verbatim plus one S7 parametrize case and 25 new S-rule, strict-load and CLI tests).
  - path: tests/test_news_impact_hostile.py
    what: NEW; replays all 33 hostile fixtures through validate_text and validate_event against the manifest verdicts.
  - path: tests/test_news_impact_sampler.py
    what: Hermetic sampler tests (tmp_path; skip cleanly when repo data is absent).
  - path: tests/test_news_impact_cluster.py
    what: Hermetic cluster-bridge tests.
  - path: tests/test_news_impact_issuer.py
    what: Hermetic issuer tests.
  - path: tests/fixtures/news_impact/hostile/
    what: 33 hostile fixtures plus the seat-owned manifest of expected verdicts.
  - path: research/prophet_v4/news_to_business_impact_20261006/phase1_designs/
    what: Accepted design packets A1-A7 (schemas pass check_schema; no forbidden key) and C2/C3 census, with a README verdict table.
  - path: agentos/decisions/DEC-NEWS-IMPACT-PHASE1-VALIDATOR-SEMANTICS.md
    what: The S1-S13 rule set and ruling R5 on the reach of the forbidden vocabulary.
  - path: .github/ci/legacy-jobs.yml
    what: news-impact-contracts job widened to engine/news_impact and the five Phase 1 test files.
  - path: agentos/workstreams/WS-PROPHET-NEWS-IMPACT.md
    what: Wave w1 done; new wave w1b (leaf modules from the A-designs) in progress; next_action moved.
verified:
  - claim: The five Phase 1 test files pass locally on the integration branch.
    command: python -m pytest tests/test_news_impact_validate.py tests/test_news_impact_hostile.py tests/test_news_impact_sampler.py tests/test_news_impact_cluster.py tests/test_news_impact_issuer.py -q
    result: 256 passed, 2 skipped (the skips are the spec-mandated hostile row and a data-absent sampler case).
  - claim: All 33 hostile fixtures reproduce their manifest verdict through validate_text, and the frozen-corpus verdicts are unchanged.
    command: python -m pytest tests/test_news_impact_hostile.py -q
    result: 33/33 validate_text rows pass; validate_event rows pass with one spec-mandated skip.
  - claim: The widened news-impact-contracts job resolves into a CI pack.
    command: python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --pack-index 0 --pack-count 12 --validate-only
    result: exit 0
  - claim: Agent OS records are schema-valid.
    command: python3 scripts/agentos.py validate
    result: 0 errors (156 pre-existing warnings, none in WS-PROPHET-NEWS-IMPACT).
  - claim: No DNR blocklist drift.
    command: python3 scripts/check_blocklist_drift.py
    result: OK
unverified:
  - The CI run on the integration PR (pending at handoff time; the seat merges on concluded green).
  - Sampler behaviour on the full-checkout data/ tree; tests are hermetic and the integration worktree is sparse.
unresolved:
  - Real-tape coverage is 243 of the 600 benchmark slots; short cells stay short and are printed, never padded.
  - No multi-source rights registry, and prospective_from is unset; economic_cluster is not cross-checked.
  - 15 QN benign rows are a disclosed exception in the hostile manifest.
  - No article-body fetch or span replay yet (Phase 2, C2 census names the receipt pattern).
  - load_strict returns a dict subclass; callers that type-check exact dict should use isinstance.
next_actions:
  - Merge the Phase 1 integration PR on concluded green, then verify landing per path against a freshly fetched origin/main.
  - Wave w1b - build thesis, mechanisms, transfer, observation, eval, agreement, cascade and prophet_adapter as leaf modules from the frozen A1-A7 designs (seat ruling - adopt each design section 7 defaults); prophet_adapter stays a leaf and is NOT wired into engine/intelligence.py before the w2 benchmark gate.
  - Wave w2 - label the 600-case benchmark with two labeler families under the A6 agreement spec, then score with the A3 eval harness; print nulls.
do_not_redo:
  - Wave-2 lanes B1-B5, A1-A7 and C1-C3 are ACCEPTED and integrated (2026-10-13); do not re-run or re-spec them.
  - The v1 contract (sha256 prefix 3edc7139) stays byte-frozen; semantic rules live in validate.py, never in the schema.
  - Do not add a second news clusterer or issuer registry; cluster.py and issuer.py bridge existing owners.
danger_areas:
  - The forbidden vocabulary (confidence, probability, score, price_target, fair_value, contagion, sentiment) is enforced at key and display reach per ruling R5; a design or lane that reintroduces it fails CI.
  - PR #6514 (propagation contract) is held by its owner; never touch it, #8697 or #8698.
  - The lane clones on ubuntu0 and ubuntu2 have empty working trees; build lanes must read R/wtx through the overlay and never write into WT or R/wtx.
  - The integration worktree is sparse (data/, site/ omitted); never git add an unexpected data/ or site/ diff.
---

# PROPHET-NEWS-IMPACT handoff 2026-10-13

Wave w1 is complete in this PR: engine/news_impact/ (validate, sampler, cluster, issuer), the
sample manifest schema, 33 hostile fixtures, five hermetic test files and the accepted A1-A7 / C2-C3
design packets. Wave w1b (leaf builds from the A-designs) runs on seat-launched Grok/GLM lanes;
its ledger is the seat scratchpad orch/launch_ledger.tsv and the next integration PR consumes it.
