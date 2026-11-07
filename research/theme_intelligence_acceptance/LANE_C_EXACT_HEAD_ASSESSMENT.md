# Lane C Exact-Head Independent Acceptance

**Lane F operation:** `theme-intelligence-f-evaluation-and-independent-acceptance-20260919-sol-001`
**Candidate operation:** `theme-intelligence-c-early-leadership-and-subthemes-20260919-sol-001`
**Carrier reviewed:** Macro Draft/HOLD PR #7455
**Candidate head:** `48156a43dfe0166ab658a99625f5b72dbd029eb4`
**Candidate tree:** `22f65ea49693890b40f7d2fcfd2fc10d7c2bf1a2`
**Candidate base:** `ca7533a67670e0393728fda4b1633b56720aa1e0`
**Implementation commit:** `d1727e80a8bead258a545ceb6d938286baf64d31`
**Verdict:** `REJECTED_FOR_REPAIR`
**Merge recommendation:** `HOLD`

## Positive evidence independently reproduced

- Production modules compile.
- Trial-registration guard passes.
- `tests/test_subsector*.py`: **102 passed, 3 skipped**.
- ThemeState/receipt/builder suite: **44 passed, 3 skipped**.
- Sector-page suite: **20 passed**.
- Parent and subtheme observations remain distinct in a mixed-strength case.
- `may_rank`, `may_gate`, `may_size`, `may_escalate`, and `may_trade` remain false.

These results prove a bounded descriptive computation capability. They do not clear the exact-head release gate.

## Repair blockers

1. **Stale reclaim evidence leaks into the current observation.** A ticker whose last observation trails the completed market session by five sessions is correctly listed under `stale_members`, but still contributes `members_with_20d_reclaim_evidence=1` and `above_20d_mean_share=1.0`. Exclude stale members from current reclaim/volume evidence or carry an explicit evidence-as-of per contribution and prevent it from being interpreted as current.
2. **Stale leadership health is not propagated through ThemeState.** `engine.neuralweb.thematic_state._read_subsector` checks only the parent rotation payload's `asof`; an embedded leadership observation from 2000 remains `MEASURED` with no stale leg when the parent payload is current.
3. **Producer failure collapses at the shared consumer.** The publisher's top-level `closed_session_leadership.status=UNAVAILABLE` and `OWNER_INPUT_LOAD_FAILED` reason are not carried into ThemeState; the consumer receives `leadership_observation=None` and no health reason.
4. **The three new test suites are dark to hosted CI.** `scripts/audit_unrun_tests.py` reports each as an unrun suite. Lane A/incumbent CI ownership must coordinate the single package-level wiring change rather than creating competing manifest edits.
5. **The return handoff is not an admissible Agent OS record.** `scripts/agentos.py validate` reports the Lane C handoff as unparseable because it has no YAML frontmatter.
6. **The candidate diff fails repository hygiene.** `git diff --check` reports eight trailing-whitespace errors in the Lane C handoff.
7. **The real-price proof is not reproducible from the carrier.** The 47-record manifest is represented only by SHA-256 `7fbd80bc049fdaa934c5d86e3047d1a2b9d9f21f8af68e680280937445b2025c` in prose. No exact manifest/result bytes are committed, so the quoted real-input table cannot be independently regenerated from PR #7455.

## Still not proven

- correction-safe first-seen and first-visible history;
- two distinct observations versus repeat renders;
- duplicate evidence-family identity when one Semiconductors observation is carried into multiple ThemeState rows;
- split/dividend/corporate-action correctness (`OWNER_CLOSE_SERIES_UNVERIFIED` remains an honest hold);
- deployed-byte/browser parity;
- predictive edge or prospective outcomes.

## Exact repair-and-return requirement

Lane C or the incumbent source owner should repair the stale-evidence and consumer-health paths, add discriminating tests, return a valid clean handoff, and make the exact real-price input/result artifact reproducible. Lane A must coordinate CI admission and consumer-contract/evidence-family mapping. Lane F should then re-pin the new exact head and rerun `lane_c_acceptance.py`; no merge, deployment, publication, or production acceptance is authorized by this assessment.

The machine-readable receipt is `lane_c_exact_head_result.json`; its SHA-256 is `a3079a57207ae310e886fda10633b2ebd24c1336c022e892b19590e27898c871`.
