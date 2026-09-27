---
workstream: "WS:GMI-MINING-M1-INTEGRATION"
session: claude/mining-seat-wave4 + claude/mining-seat-wave5 (one seat, 664a0650, same day)
model: opus
ended_because: blocked
mission: >
  Own PR #7950 (T04a) to MERGED and PRODUCTION_PROOF for
  gmi-mining-fable-ceo-m1-integration-20260924-chairman-001, then land the records wave that
  #7950's own in-flight CI had been blocking: table the rulings the seat had measured but could
  not push, and mint the program's execution record against the forty MGD obligations. A
  secondary and unplanned mission took priority mid-session: retracting a merge justification
  this seat had got wrong, before the wrong rule reached another lane.
state_before: >
  PR #7950 (T04a) at head c05368b31a6, 13 ci-pack-* SUCCESS and 2 IN_PROGRESS, watcher
  bt3a9t2uu armed. Records PR #8060 merged b95cfc873a4 at 02:56:02Z and believed clean. Rulings
  on main reached R-MIN-33f. R-MIN-34 measured but untabled, because tabling it needed a push to
  #7950 while its CI was in flight. Five freeze packets (T02/T03/T04b/T07/T08) written but held
  in a session scratchpad, so not durable. T02 gated on another seat's #7905; T05/T06 on #7870.
changed:
  - path: engine/market_ontology/mining_theme_research.py
    what: "WAVE 5. `_summarize_status` takes a new `has_named_absence` keyword
      (`bool(bundle.omissions)` at the sole call site) and the `stream_threshold_unknown`
      readiness clause is scoped to it, with `has_native_blocks` tested first; the
      duplicated `if not limitations: return 'degraded'` tail is collapsed (R-MIN-34 had
      already measured it unreachable for this input). Closes a real defect: because the W-R
      slice vocabulary mints `stream_threshold_unknown` on EVERY payload, the unscoped early
      return fired before the native-block channel was consulted, so every rare-earth
      dossier reported `ready` over a wholly empty economics panel while copper degraded on
      identical input. Root cause: that code has TWO minting sites - the omission map (a
      fact about the bundle) and the slice vocabulary (a per-slice CONSTANT) - and
      `limitations` is a flat list that cannot tell them apart. Also gates the headline
      'the contract explanation is retained' on a non-degraded status, because that
      sentence was asserting retention over an empty panel."
  - path: tests/test_mining_composition.py
    what: "WAVE 5. Adds
      `test_mgd08_clause2_wholly_empty_economic_path_degrades_on_both_slices` - MGD-08
      clause 2, two-armed across BOTH delivered slices. The populated arm is a positive
      control and is load-bearing: without it a pipeline that degraded everything would
      satisfy the empty arm vacuously. Also pins that the empty collection mints no
      fabricated `industry_total` and that a degraded payload is still schema-VALID."
  - path: research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md
    what: "R-MIN-34 tabled (MGD-08 clause 2: degraded + native_blocks == [] + the NAMED absence SATISFIES 'fails'; a hard refusal is the wrong target because it contradicts R-MIN-15 and destroys the source-only usefulness MGD-11 requires; two-armed pin specified; casebook-cannot-express construction note; the seat's own silently-ignored-override measurement error recorded against it). R-MIN-33g tabled, which AMENDS the already-shipped R-MIN-33f."
  - path: research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json
    what: "New. The program's execution record against all 40 MGD obligations, minted because the canonical trace is owned by carrier #7795 and is not reachable from main. Cites that trace by commit + blob + sha256 and records reachable_from_main false / seat_may_modify false. One row per obligation id with an explicit status word; status is never inferred from a test name. COVERAGE IS OBLIGATION-LEVEL: the first version credited coverage with a TASK-level test, and the carrier trace carries task T04 for all eight T04 rows with no a/b split (the split is R-MIN-05's), so it credited all eight to T04a's merge. Every verdict happened to be right, but a right answer from a bad rule would credit a T04b row the same way next wave. Each COVERED row now names the DELIVERED test id that pins it and the generator asserts that test exists in the suite - which also makes the rename gap visible per row: 4 of the 5 covered obligations are pinned by tests RENAMED from their planned names, which is exactly why a name audit cannot measure this program."
  - path: research/mining/m1_integration_program/T02_FREEZE_PACKET.md
    what: "Moved from the session scratchpad into the program record so it survives the session."
  - path: research/mining/m1_integration_program/T03_FREEZE_PACKET.md
    what: "Same. Carries the exact truth table, the six anti-letter-gaming rules, and the MGD-10 obligation added 09-27. Plus a new §0 fixing a VACUOUSLY SATISFIABLE guard the seat found by auditing every packet symbol against main: the truth table asserted `assess_management_sequence` is never called, and that symbol exists nowhere in code - only in audit prose - so the guard would have reported green for free while the real projector ran. Corrected to the measured seam (extract_guidance stays bound to _no_guidance, issuer_profiles.py:177)."
  - path: research/mining/m1_integration_program/T04B_FREEZE_PACKET.md
    what: "Same. SEAT-AUTHORED because neither audit ever froze a T04b spec - Audit B wrote ONE spec for all of T04 and the a/b split is R-MIN-05's. Freezes four seams a lane would otherwise decide silently."
  - path: research/mining/m1_integration_program/T07_FREEZE_PACKET.md
    what: "Same."
  - path: research/mining/m1_integration_program/T08_FREEZE_PACKET.md
    what: "Same, plus a new §8 recording what this wave landed against its §3 gap, §5 table and §6 findings, and retracting a seat summary that had said '6 COVERED' where §5 itself says 5."
  - path: agentos/workstreams/WS-GMI-MINING-M1-INTEGRATION.md
    what: "Advanced at the wave boundary. MIN-W2 and the top-level next_action both still described #7950 as READY-not-merged at head 64a0b1dd - a head two revisions stale and a state two ladder rungs behind the evidence. Now records T04a at PRODUCTION_PROOF, states the dispatch position explicitly, and adds the two do_not_redo entries and two landmines this wave paid for."
  - path: agentos/handoffs/GMI-MINING-2026-09-26-m1-integration.md
    what: "CORRECTED AT SOURCE rather than only superseded. A refuted claim that still reads as standing guidance gets applied by the next lane that finds it - the same defect as R-MIN-33f. An appended correction banner refutes its '#7950 unblocks T04b' line and its '>= 8 ci-pack-*' watcher prescription, and states that nothing else in it is withdrawn."
  - path: "research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md (second edit)"
    what: "R-MIN-33f's own row now says 'clause 2 AMENDED BY R-MIN-33g' in its header cell and carries the amendment inline. Adjacency was not a correction: 33g sits on the next line, but 33f's own text still told a reader to use the unsatisfiable pack floor and said nothing about re-reading after a push."
  - path: "research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json (wave 6)"
    what: "SUBJECT-LEVEL RE-AUDIT. 30 rows were statused NOT_RUN from the note 'Owning task <T> has not landed on main' - a TASK-level verdict on an obligation-level question, which this file's own authority block already forbids in the CREDITING direction and had never closed in the denying one. Re-measured by subject, clause by clause: MGD-15/16/17/21/22 -> PARTIAL_BY_CONSTRUCTION, MGD-20 -> SATISFIED_BY_ABSENCE_OF_CAPABILITY, MGD-19/23 keep NOT_RUN with rewritten reasons. NOT_RUN 30 -> 24; UNPINNED stays 0 of 40; counts rederived from rows. Two new authority keys state the four-places rule and BOUND the audit's scope - 9 rows re-measured, 8 read and adjudicated unchanged, 23 explicitly NOT subject-measured."
  - path: "research/mining/m1_integration_program/T08_FREEZE_PACKET.md (wave 6)"
    what: "The sentence that CAUSED the six wrong statuses is withdrawn at source: 'T02/T03/T05/T06/T07/T08 rows are not reconciled here ... a reconciliation would be fiction.' It sat in the ACCEPTANCE task's own freeze packet, so it would have governed the T08 lane that read it. Replaced by the four-places test, plus eight new rows (15/16/17/19/20/21/22/23) in the SS5 table so a T08 lane meets the corrections on the path it actually travels, plus SS6.4."
  - path: "tests/test_mining_composition.py (wave 6)"
    what: "Delivered test_mgd17_refused_comparison_does_not_delete_the_supported_facts - the one piece of MGD coverage work available while both #7870 and #7905 are closed. MGD-17 clause 2 ('refuses dependent arithmetic WITHOUT deleting supported facts') was measured true but asserted nowhere. The test carries a positive CONTROL arm: the same bundle composed without the bad comparison must yield an identical native-block list, because 'the block survived' proves nothing if the pipeline keeps blocks unconditionally. Suite 174 -> 175 passed."
  - path: "research/mining/m1_integration_program/rulings/R-MIN-2026-09-24-wave1.md (wave 6)"
    what: "R-MIN-36 records the re-audit, the repealed sentence, the per-row evidence, and the two corollaries that each cost a wrong verdict in this same wave: a delivered test whose docstring cites an obligation may still not PIN it (helper vs composed payload), and a pinned clause may not be the OPERATIVE one."
  - path: "research/mining/m1_integration_program/MGD_EXECUTION_STATUS.json (wave 7)"
    what: "CLOSED the audit wave 6 bounded. The 14 rows left with owning-task notes were measured by subject, plus the 8 wave 6 had READ without writing their evidence onto the rows (its MGD-13/14/25 measurements lived only in R-MIN-36 - the third time this program shipped a correction to a place the reader does not travel). Six more rows MOVED to PARTIAL_BY_CONSTRUCTION on delivered, green, CONTROLLED pins: MGD-05/24/27/28/29/30 - twelve of forty moved in total. The remaining 18 each carry one of three MEASURED reasons stated on the row: subject-absent (own vocabulary at zero occurrences), G2-gated (the unit is a real-source demonstration no test may satisfy), operative-clause-blocked (a later clause is unviolatable while the FIRST needs T02's unlanded vocabulary). Counts 6/1/18/12/3 = 40, UNPINNED 0. The apply script ASSERTS that no owning-task boilerplate survives on any row."
  - path: "research/mining/m1_integration_program/T08_FREEZE_PACKET.md + rulings (wave 7)"
    what: "SS5's wave-6 caveat ('do not read this table as a completed 40-row subject audit') is withdrawn at source and replaced by the wave-7 outcome, grouped by measured reason. R-MIN-37 records the closure, the six moves with their evidence, the two deliberate NON-moves (MGD-35: absent wiring is not a guarantee about future wiring, and the row's value is that it is owed; MGD-38: half a demonstration is none), and the method finding - a measurement belongs on the ROW, a ruling records why."
verified:
  - claim: "MGD-08 clause 2 was NOT satisfied by the delivered code on the rare-earth
      slice. R-MIN-34's 'NOT a code defect' held on W-C only, and its evidence cell
      measured the copper limitation set."
    command: "compose_mining_research on synthetic_case('copper_complete') and
      synthetic_case('rare_earth_complete'), each with
      dataclasses.replace(bundle, financial_packets=()); dumped summary.status,
      economics.status, native_blocks, derived, reported_economic_context, industry_total
      (scratchpad/probe_mgd08c.py and probe_mgd08d.py)"
    result: "W-C summary.status 'degraded'. W-R summary.status 'ready' with native_blocks
      0, derived [], context_block_count 0, industry_total None, and the headline 'the
      contract explanation is retained; the stream threshold is unknown' - a readiness
      claim over a panel with nothing in it. reported_economic_context.notes is non-empty
      even in the copper DEGRADED dump, so it is a constant policy string and not
      retained content."
  - claim: "Fixing it does NOT weaken MGD-18 / R-MIN-15 / plan §6, because the two
      obligations have DIFFERENT SUBJECTS. This is the fact that settled the
      obligation-versus-obligation question."
    command: "len(synthetic_case('missing_stream_threshold').bundle.financial_packets);
      then pytest that case's pin before and after the change"
    result: "len == 1 - a packet IS submitted and is withheld pending the threshold,
      expected signed_native_blocks == []. So MGD-18's subject is a withheld submission and
      clause 2's subject is a path that submitted nothing.
      test_missing_threshold_keeps_contract_explanation stays GREEN throughout."
  - claim: "The pin is genuinely falsifiable, and the fix changes no shipped case."
    command: "pytest the new test before the fix; then the blast-radius sweep over all 11
      CASE_NAMES comparing current status against the new ladder
      (scratchpad/probe_blast_radius.py); then all 7 mining suites"
    result: "Before: FAILED with AssertionError: ('rare_earth_complete', 'ready') - the
      copper arm passed, so the pin is not universally red. Blast radius: ZERO of 11 cases
      change status, because every shipped case submits >=1 packet ('source_only' submits 0
      but mints no threshold code and was already degraded) - which is precisely why a
      green 53-case suite never caught this. After: 174 passed across the 7 mining suites.
      Sole importers of the module are those suites; no production consumer exists yet."
  - claim: "An independent Opus review REFUTED the seat's first discriminator, and the
      refutation was verified independently before being accepted. The shipped
      discriminator is the NAMED-ABSENCE receipt, which is R-MIN-34's own bar."
    command: "scratchpad/verify_reviewer_f1.py - re-ran the four junk-packet shapes on both
      slices, then compared every one of the 11 casebook statuses against an
      any-omission ladder, then checked the strict variant the review warned against"
    result: "F1 CONFIRMED: with `has_economic_input = bool(bundle.financial_packets)`, four
      shapes still returned `ready` on W-R with native_blocks 0 and expectations 0 - an
      empty mapping, `value: None`, a non-numeric value, and a mev-only packet - because the
      module routes each out of every channel while the predicate still counted it as
      submitted. `bool(bundle.omissions)` reproduces all 11 shipped statuses with ZERO
      mismatches and degrades all four shapes on both slices. The strict variant
      `'stream_threshold' in omissions` was REJECTED on measurement: it flips
      same_horizon_revision and page_generation_change to degraded. 174 passed after."
  - claim: "PR #7950 merged on CONCLUDED green, not mid-flight - the distinction this session learned the hard way."
    command: "gh run list --workflow ci.yml --branch claude/min-t04a-definitions --json headSha,status,conclusion (selected on head c05368b31a6)"
    result: "run 36288053731 completed / success; then 26 checks with 0 pending and the sole red ci-authority/codex/merge-queue-pilot (sanctioned spurious)"
  - claim: "#7950 is MERGED and its merge commit is an ancestor of origin/main."
    command: "gh pr view 7950 --json state,mergedAt,mergeCommit; git merge-base --is-ancestor aff8b76cba6 origin/main"
    result: "MERGED aff8b76cba6afa6ed03298a1814b059e317070a0 at 2026-09-27T03:33:28Z; ancestor YES"
  - claim: "T04a is at PRODUCTION_PROOF - Audit B's frozen GREEN gate passes against main's own bytes, not the PR's."
    command: "git checkout -b claude/mining-seat-wave4 origin/main && python3 -m pytest tests/test_mining_composition.py -q"
    result: "53 passed in 7.17s (43 test functions; one is parametrized into 11 cases)"
  - claim: "The 40-obligation map still partitions exactly, checked against the carrier trace itself rather than against this program's prose."
    command: "git show origin/sol/...:research/mining/MINING_IMPLEMENTATION_TRACE_2026-09-24.json | python3 (group by task)"
    result: "T01 2, T02 3, T03 8, T04 8, T05 4, T06 4, T07 5, T08 6 = 40; 40 unique ids"
  - claim: "#8060 was merged MID-FLIGHT. The docs-only --admin exception did NOT apply."
    command: "gh run view 36288860409 --json jobs; gh api repos/.../commits/1081ffed2fe --jq .commit.committer.date"
    result: "ci-plan SUCCESS in 3m56s planning contract-delta + ci-pack-0 + ci-pack-1, all in_progress at the 02:56:02Z merge; head committed 02:33:16Z, run created 02:33:32Z (16s later); two earlier runs on the branch cancelled by the seat's own pushes"
  - claim: "All five COVERED_SUITE_GREEN verdicts were re-derived at obligation level against the delivered suite, not inferred from the owning task."
    command: "read the carrier trace task field for every T01/T04 row, then grep the delivered def test_* names out of tests/test_mining_composition.py"
    result: "The trace carries task T04 for ALL EIGHT T04 rows and no a/b split, so the task-level rule credited eight rows when only T04a landed. Re-derived per obligation: MGD-09 is pinned by test_missing_issuer_refuses_financial_join (planned name was test_security_without_issuer_refuses_financial_join), MGD-11 by test_source_only_business_stays_useful (the only name that agrees), MGD-12 by test_duplicate_local_asset_labels_are_not_additional_supply, MGD-34 by the two authority_literal_false tests one per witness slice, MGD-39 by test_partial_coverage_industry_total_stays_null plus the two industry_total_unknown tests. All five stand and no count moved (5/1/30/1/2/1 = 40); the justification changed from task-level to a named delivered test id, asserted present in the suite."
  - claim: "Every code symbol the four dispatch packets name was resolved against main, and exactly two turned out to be audit vocabulary rather than code - one of them inside an assertion, which made that assertion vacuously satisfiable."
    command: "grep -rl <symbol> engine tests contracts, for each identifier extracted from T02/T03/T04B/T07_FREEZE_PACKET.md"
    result: "Four misses total, and the pile they fall into is the whole point. DEFECT (1): assess_management_sequence appears ONLY in audit prose, the rulings and the packets quoting them - never in code - yet T03's truth table required it to be 'never called', so the requirement greps to nothing and passes for free while the real projector runs. Fixed against the measured seam, issuer_profiles.py:151 _no_guidance and :177 extract_guidance. NOT-A-SYMBOL but harmless (1): projector_unbound is likewise absent, but it names a typed refusal T03 MINTS, so it is a thing to create, not to look up. NOT-YET-MINTED, correct (2): MINING_PRIVATE_RIGHTS_PROFILE (T02 mints it) and DISCOVERY_TICKERS (held for #7870), plus fcx_issuer/mp_issuer/mining_private_registry/fcx_profile/mp_profile/FCX_CIK/MP_CIK/MINING_TICKERS - every one now labelled in its packet and restated as the dispatch preflight, because a lane cannot otherwise tell not-yet-minted from wrong-name. profile_for_ticker resolves in the SHARED issuer_profiles.py, not the mining module, consistent with it being #7905's hunk. And R-MIN-34's construction note is now verified against real code rather than a probe: tests/mining_casebook.py:43 _merge is merge-only with no delete, :76 sets financial_packets from the presence of the top-level economics key, :83 synthetic_case - which is exactly why a bundle={...} override is silently ignored. Every T04b and T07 symbol resolves."
  - claim: "Every NEGATIVE assertion across all five freeze packets was swept, not just the one that was already broken - a negative assertion is SATISFIED by a wrong subject name, unlike a positive one that fails loudly."
    command: "regex sweep for never/must not/may not/no invented/does not appear/forbidden across the five packets, pull each backticked identifier, resolve against engine tests contracts .github"
    result: "10 subjects resolved, one real miss beyond the already-adjudicated set: `next_outlook` in T03 section 3 - the CONDITION side of the row whose ASSERTION side was fixed earlier. It is a source-document concept, not a field, so a lane omitting a field that never existed meets the condition trivially and the refusal it then sees proves nothing. Re-expressed on the fixture (the source carries no forward figure of any kind) with the explanation in section 0. The sweep also flagged `planned_test`, which is a real field in MGD_EXECUTION_STATUS.json and only looked absent because the search roots omitted research/ - that scope limit is now recorded in the packet for whoever re-runs it."
  - claim: "T02's gate can be checked against MAIN instead of against #7905, and the check says the gate is real and not stale. T02's oracle also turns out to describe a shape that does not exist yet."
    command: "read profile_for_ticker in engine/company_intelligence/issuer_profiles.py on main; count fiscal_scope in that file; count raise in the function body; count definitions of the name"
    result: "def profile_for_ticker(ticker: str) -> IssuerProfile or None at :1293, the ONLY definition. fiscal_scope occurs ZERO times in the whole file; the body contains ZERO raise statements and returns None for an unknown ticker; there is no private/public branch at all, just an AAPL special case then _HOMEBUILDER_PROFILE_FACTORIES.get (:1272, identity twin at :128); and there is NO registration seam - no register_profile, no plugin hook, both dicts are module-level literals and __all__ at :1307 lists every symbol by hand. So T02's truth table and its mutant (d), which speak of a private branch requiring fiscal_scope and raising ValueError, describe the POST-#7905 shape. The packet is not wrong - #7905 introduces the split and T02 appends into it - but it never said so. Recorded as a structural precondition in the packet."
  - claim: "The mid-flight defect is isolated to #8060 and did not affect the seat's other merges."
    command: "gh run list --workflow ci.yml --branch claude/mining-seat-wave2-records (selected on #8053 head ea29419ab81)"
    result: "run 36283494517 completed / success, created 00:46:08Z; #8060's sibling #8053 merged 01:31:59Z, i.e. after its own proof concluded"
  - claim: "#8060's surviving proof run concluded FAILURE, and main is nevertheless NOT red. The red was an ordering artifact confined to that PR's merge ref, and NO heal is owed."
    command: "gh api .../runs/36288860409 (conclusion=failure; ci-pack-0 + ci-gate red); gh run view --job 108539369229 --log-failed; git ls-tree origin/main -- research/mining/m1_integration_program/reviews/; git cat-file -e b4068812aa38:<that review file>; MACRO_MASTERMIND_REPO=/nonexistent MACRO_TERMINAL_REPO=/nonexistent python3 scripts/agentos.py validate"
    result: "ci-pack-0 selected ONE job, self-mod-fence, whose step 'agent-os record contract' exited 1 on a single test: tests/test_agentos_schema.py::test_cross_repo_path_is_unchecked_when_that_checkout_is_absent, AssertionError 'phantom-artifact' not in stdout. The phantom was THIS PROGRAM'S OWN record - WS-GMI-MINING-M1-INTEGRATION.md artifacts entry 'research/mining/m1_integration_program/reviews/OPUS_T04A_PR_REVIEW_R3_2026-09-26.md' - which is ABSENT from #8060's base b4068812aa38 and was added to main by aff8b76cba6a (#7950, T04a). So #8060 named a file its in-flight SIBLING was carrying. origin/main (7742e508244) now holds both the record and the file, so the phantom is gone from main; a validate with both sibling checkouts absent leaves 9 phantoms, ALL under data/ site/ verify_shots/ and ALL tracked on origin/main, i.e. sparse-worktree artifacts only. Main carries no macro-repo phantom."
  - claim: "Six MGD rows were mis-statused NOT_RUN while their subjects are delivered on main."
    command: "PYTHONPATH=<worktree> python3 scratchpad/probe_mgd15.py; probe_t03_seven.py; probe_t03_confirm.py"
    what: "MGD-15: -375 submitted -> -375 composed, sign '-', no coercion. MGD-16: a leg missing `unit` withholds the row AND mints definition_unqualified:unit (minted at mining_theme_research.py:802, the COMPARISON channel, delivered by T04a). MGD-17/20: economics['derived'] is the literal [] on all 11 casebook cases. MGD-21: next_period_outlook -> missing_derivation, 0 expectations, 0 blocks, and `assess_management_sequence` does not exist in the tree. MGD-22: is_range/is_consensus are const:false and _BADGE_VOCABULARY gates the headline. MGD-19: a packet measure='intersegment elimination' value=-120 DOES compose a block with sign '-', so the construct exists and only a fixture is missing. MGD-23: 'financing proceeds' composes verbatim - the composer is a passthrough."
  - claim: "MGD-15 clause 2 is not expressible on main, so the row is PARTIAL and not COVERED."
    command: "binding.publication_harness().shared_contract()"
    what: "MiningResearchRefusal: shared_contract_unavailable - engine.theme_graph.curation_assertion is not importable on this checkout (ModuleNotFoundError). I had drafted this row COVERED_SUITE_GREEN; this seam refuted it before it shipped."
  - claim: "Every pin cited in the ledger is green, and the new MGD-17 pin passes."
    command: "python3 -m pytest tests/test_mining_*.py -q  (and -k on the 14 named ids)"
    what: "175 passed (was 174). The 14 named pins all PASSED individually. python3 scripts/agentos.py validate -> 0 errors."
  - claim: "The mining artifacts were unchanged by main moving under the ledger's recorded base."
    command: "git diff --stat f2a2abf706026b18594012f9477552482b14dd05 origin/main -- <mining module, kernel, schema, tests>"
    what: "Empty. origin/main advanced to e59c8b4bde2b but no mining artifact moved, so measured_against stays valid."
  - claim: "T02's gate is still CLOSED, measured without reading #7905."
    command: "git grep -c fiscal_scope origin/main -- '*issuer_profiles*'"
    what: "No match - 0 occurrences in any issuer_profiles source on origin/main. The term appears only in prose/records."
  - claim: "Six more rows had delivered, green, CONTROLLED pins while statused NOT_RUN."
    command: "grep the delivered sources for each obligation's own vocabulary, then read every candidate test BODY"
    what: "MGD-29 is the strongest: `mining_dependency_binding.py:286-320` discards `entitled` (`del entitled`) and returns `route_unbound` with `read_count == 0`; `test_route_unbound_refusal_is_identical_for_entitled_and_unentitled_callers` asserts the two refusals are EQUAL objects, and `test_probe_route_unbound_reports_the_harness_read_counter` sets `harness.read_count = 3` and requires 3 - a positive control proving the zero is measured. MGD-30: `live_admission == 'refused'` for every parametrized case. MGD-24: `system_replay` without a cutoff raises `replay_cutoffs_required` while `latest` with both cutoffs None validates. MGD-27: a refresh pairing changed quantities with stale causal text refuses `generation_changed`. MGD-28: `expected_generation_required` is mandatory for a paged read, admitted unpaged. MGD-05: `SLICE_ANCHORS` binds copper to `theme:copper_steel_electrify` and a rare-earth anchor on the copper slice refuses `slice_theme_mismatch`."
  - claim: "The other 18 rows' NOT_RUN is measured, not assumed."
    command: "case-insensitive term census over module + binding + schema + all 7 mining suites"
    what: "MGD-26 (milestone/target/achieved/deadline/elapsed), MGD-31 (revoc/warm/emission), MGD-32 (logout/account_change/cross_user), MGD-33 (source_map/analytics/telemetry), MGD-36 (keyboard/focus/mobile/theme_dark) and MGD-40 (acceptance/deploy/production_proof) all measure ZERO occurrences. MGD-35's two `incumbent` hits are both PROSE in the binding docstring, never code. MGD-30's four `fallback` hits are a cik fallback and a `source_label` fallback, neither an admission path - which is why its clause 2 is unviolatable rather than asserted."
  - claim: "PR #8100 (waves 5+6) merged on its own concluded-green proof and is verified on main."
    command: "watcher tick 12: run 36357513314 completed, 12 packs, CLEAN; gh pr merge 8100 --squash; git show origin/main:<ledger>"
    what: "Merged 2026-09-27T23:35:40Z as ce0065d89732. On origin/main the ledger reads counts 6/1/24/6/3, MGD-17 PARTIAL_BY_CONSTRUCTION, both new authority keys present, and the new MGD-17 pin present in tests/test_mining_composition.py. The only red was `ci-authority/codex/merge-queue-pilot`, which is red by design on every main-targeting PR and excluded by name in merge_on_green.py."
unverified:
  - claim: "This records PR itself reaches MERGED."
    what_would_verify: "The corrected watcher (scratchpad/watch_pr.sh, keyed on the run's own status for the exact head sha) exits 0, then the files resolve on origin/main."
unresolved:
  - "T02 cannot start and nothing in this program can advance past it until CDV-1 #7905 reaches main. That is another seat's DRAFT under its own audit, so this program has no lever on it at all - not a lane to work, a dependency to wait out."
next_actions:
  - "Own THIS records PR to MERGED, then verify the files on origin/main. Use the corrected watcher: the expected check set is the ci.yml RUN's job list for the exact head sha and completion is that run's status == completed. Do NOT use a constant pack floor (R-MIN-33g) and do NOT read zero packs as proof that no packs will come - ci-plan takes about four minutes to publish the plan."
  - "RESOLVED - do NOT re-open this as a heal. Run 36288860409 concluded FAILURE (ci-pack-0, then ci-gate downstream of it) and main is NOT red: the phantom-artifact that reddened it was fixed by #7950 landing the file three minutes later, and origin/main carries both halves. The inference this handoff previously stated - proof run red therefore main red therefore heal owed - is WRONG and is withdrawn. A surviving proof run tests a MERGE REF pinned to that PR's base, which is a state main has already outgrown; re-derive the failure against current main before believing it."
  - "T02 is still the only next dispatchable TASK and is still gated on #7905, another seat's DRAFT, which must never be polled. Before dispatching T02, delete plan §4 bullet 1 (Audit A F1's unauthorized source-acquisition act). Correcting the 09-26 record: #7950's merge unblocks NEITHER T03 NOR T04b - R-MIN-05 orders T01' -> (T02 || T04a) -> T03 -> T04b -> T07, so T04b comes after T03 and T03 additionally needs T02 delivered."
  - "CORRECTED 2026-09-27 (wave 5). T04b owes the two-armed MGD-10 pin ONLY. The MGD-08 clause 2 pin is DELIVERED - it is not T04b's to write, and T04B_FREEZE_PACKET 4.4 now carries a DO-NOT-RE-PIN banner. MGD-10 is still genuinely deferred: T04B_FREEZE_PACKET 4.2 carries `period` onto native blocks, and that is what makes MGD-10's second arm expressible, so the pin must land in the same PR as the field. Closing MGD-08 also required a BEHAVIOUR change (see R-MIN-35), which the superseded action did not anticipate."
  - "T08 lane: SUPERSEDED BY WAVE 7 - the SS5 table plus the ledger now cover ALL 40 rows by subject, and the 23-row audit surface named below is CLOSED. What still binds from this entry is its RULE (reconcile by subject, never by owning task) and its prohibition (do not re-derive statuses from the carrier trace's `task` field). Superseded text: the SS5 reconciliation table is now authoritative for 18 of 40 rows and its closing RULE changed - reconcile by SUBJECT clause by clause, never by owning task. Do NOT re-derive statuses from the carrier trace's `task` field. The 23 rows listed as NOT individually re-measured in the ledger's scope_of_the_2026_09_27_subject_reaudit key are the remaining audit surface; each is a bounded subject measurement, and several may move "
  - "MGD-17 clause 1, MGD-20 and MGD-22 each owe a pin IN THE SAME PR as the field that makes them falsifiable: the first PR that populates `economics['derived']` owes MGD-17 clause 1 + MGD-20, and the first that mints a `house forecast` field owes MGD-22. MGD-15 clause 2 owes its pin in the PR that lands #7870's shared assertion contract. These are recorded ON the rows, not only here."
  - "A T03 lane owes MGD-19 a PAYLOAD-level fixture (an intersegment elimination row in the casebook), not another helper assertion - and must NOT credit test_internal_transfer_keeps_elimination_sign, which calls _signed_value directly. It owes MGD-23 the input-kind vocabulary (financing / cash availability / owned inventory / operating earnings) BEFORE any non-substitution pin, because the composer currently passes `measure` through verbatim and so can neither substitute nor enforce."
  - "Operator items still open and not seat-actionable: mini2 WAN routing fix, mini2 MiniMax provisioning, mini2 keychain unlock for cursor-agent."
do_not_redo:
  - "Do not re-open MGD-08 clause 2, and do not revert it to UNPINNED to satisfy T08
    acceptance item 3 - that item is amended and MGD-08 is exempt. It is
    COVERED_SUITE_GREEN, pinned two-armed across both slices by a test that failed before
    the fix and passes after, and R-MIN-35 records the measurement. The ledger's UNPINNED
    count is now 0 of 40."
  - "Do not 'restore' the unscoped `if \"stream_threshold_unknown\" in limitations:
    return \"ready\"` early return as a fix for anything. It is what made every W-R
    dossier claim readiness over an empty panel. R-MIN-15's intent - a missing threshold
    must not destroy the contract explanation - is preserved by the scoped clause, and
    test_missing_threshold_keeps_contract_explanation proves it."
  - "Do not re-spec or re-review T04a. #7950 is merged and proven green on main (53 passed). Rounds 1-3 and three Opus reviews are spent; R-MIN-31/32/33/33a-33f are tabled."
  - "Do not rebuild the shared base. #7870 owns theme-graph / evidence / rights; Mining CONSUMES it and mints no shell, evidence or rights vocabulary (R-MIN-21's DO-NOT-CREATE list is literal)."
  - "Do not re-derive the MGD partition by grepping test names. It resolves 0/40 on main and 2/40 at #7950, so a name audit reports 38 false gaps. MGD_EXECUTION_STATUS.json is keyed by obligation id for exactly this reason."
  - "Do not re-open the docs-only --admin question. It is settled by R-MIN-33g: the exception needs a diff that triggers NO RUN AT ALL, established from the Actions API."
  - "Do not re-audit the nine rows this wave measured (MGD-08/15/16/17/19/20/21/22/23) or the eight it read and left unchanged (MGD-02/03/05/06/07/13/14/25). Each carries its measurement and its evidence in the row note. A fresh session is not a material invalidator."
  - "Do not re-status MGD-15 COVERED_SUITE_GREEN. That was my first draft and the shared-contract seam refuted it: clause 2's subject is absent from main until #7870. The refutation is recorded inside the row so it cannot be lost."
danger_areas:
  - "A SLICE-LEVEL VOCABULARY CODE THAT SHORT-CIRCUITS A STATUS LADDER MAKES THAT LADDER
    BLIND ON THAT WHOLE SLICE. `stream_threshold_unknown` is minted on every W-R payload by
    the slice's own definitional vocabulary, so an early `return \"ready\"` keyed on it
    answered for every rare-earth request before the native-block channel was ever read -
    and W-C, which never mints that code, behaved correctly, so the suite's two positive
    witnesses agreed and the defect was invisible. When a ladder branches on a limitation
    code, check whether any slice mints that code UNCONDITIONALLY; if it does, the branch
    is a per-slice constant, not a condition. Ordering matters as much as the predicate:
    put the CONTENT test (has_native_blocks) above any explanatory-code test. The deeper
    form: `stream_threshold_unknown` has TWO minting sites - the omission map, where it is a
    fact about this bundle, and the slice vocabulary, where it is a constant - and
    `limitations` is a FLAT LIST, so by the time the ladder reads it the provenance is gone.
    Branch on the source (`bundle.omissions`), not on the merged list."
  - "'SUBMITTED' IS NOT 'CONTRIBUTED'. The seat's first fix keyed readiness on
    `bool(bundle.financial_packets)` and an Opus review refuted it with four measured
    shapes: an empty mapping, `value: None`, a non-numeric value, and a mev-only packet are
    each routed out of every channel of the dossier, yet each satisfied the predicate, so
    W-R still claimed `ready` over an empty panel. The drop site mints NO limitation, so a
    dropped packet leaves no trace anywhere in the payload. CORRECTED the same day: that
    silence is a DELIBERATE ruling (R-MIN-31 §I reserves `definition_unqualified:*` for
    DEFINITION fields and assigns a missing measurement datum to the bundle's omission
    mapping), and the residual state it leaves - an unrelated named omission plus a junk
    packet reading `ready` - is SATISFIED under R-MIN-34's named-absence bar, not open. Do
    NOT 'gate on input that reached an output', which is what I first wrote here:
    `missing_stream_threshold` submits one packet that reaches NO output - 0 native blocks
    and 0 expectations - and plan §6 VERBATIM requires it `ready`, so a contribution gate
    breaks the plan. Closing that state requires amending R-MIN-31 §I or plan §6, which is
    an adjudication for the obligations' owner and never a lane's patch."
  - "A STATUS FUNCTION CANNOT HONOUR A DISTINCTION ITS ARGUMENTS CANNOT EXPRESS.
    `_summarize_status(limitations, has_native_blocks)` was asked to separate 'submitted and
    withheld' from 'submitted nothing', and both states arrive as (threshold code present,
    has_native_blocks False) - identical inputs, so necessarily identical output. Before
    ruling that a behaviour already satisfies an obligation, check that the deciding
    function can even SEE the obligation's discriminator. R-MIN-34 ruled on behaviour it
    measured on one slice and could not have distinguished on the other."
  - "Two obligations that look contradictory may simply have different SUBJECTS, and the
    fixture is where you find out. MGD-18 ('missing threshold keeps the contract explanation
    -> ready', no native blocks) read as a direct contradiction of MGD-08 clause 2 ('a
    wholly empty economic path fails') until `len(bundle.financial_packets) == 1` on case
    `missing_stream_threshold` showed its subject is a WITHHELD submission, not an empty
    path. Read the fixture's inputs before adjudicating an obligation conflict or weakening
    either side."
  - "A case-insensitive grep for HOLD produces FALSE POSITIVES on ordinary domain vocabulary - 'threshold' and 'withholding' both contain it, and #7950's body is full of stream_threshold_unknown. A pre-merge hold check must be anchored (HOLD-FOR-SOL, word-boundary HOLD, 'do not merge'). An unanchored match nearly blocked a lawful merge here."
  - "gh api .mergeable returns EMPTY as a matter of course because GitHub computes mergeability lazily. An empty answer is not 'false' and is not a result; this seat once read blank mergeable ticks as a failing API."
  - "Never touch carrier #7795's branch sol/mining-principal-research-20260923. MGD_EXECUTION_STATUS.json deliberately CITES it (commit + blob + sha256) rather than copying or editing it."
  - "engine/company_intelligence/mining_issuer_profiles.py does NOT exist on main. T02 mints it and T03 only extends it (Audit A lines 73 and 125), so any lane told to 'extend' it before T02 lands will either create it or collide."
  - "A lane dispatched on T02 that greps main will find profile_for_ticker has no fiscal_scope, no private/public branch and no raise, because that split is CDV-1 #7905's hunk. It must NOT build the split itself - that is another program's hunk in a shared file its incumbent owns. The absence IS the gate: no fiscal_scope in issuer_profiles.py means #7905 has not landed and T02 is not dispatchable. Check it that way, against main, never by reading #7905."
  - "The shared dispatcher is the legacy-jobs.yml append-LAST problem in Python. There is no registration seam, so every sector program edits the same four sites (:128, :1272, the two *_for_ticker bodies, __all__) and whoever lands second conflicts. Also do not put FCX or MP into a dict named _HOMEBUILDER_* - the wrong-but-easy move the current shape invites; Mining tickers belong in Mining's own mapping."
  - "An `artifacts:` entry must name a file THIS PR carries or one already on main - never one an in-flight SIBLING PR is carrying. `agentos.py validate` reports a missing one as a WARNING (joins fail open), so '0 errors' never catches it, but `self-mod-fence` is ALWAYS-ON (unscoped) and tests/test_agentos_schema.py::test_cross_repo_path_is_unchecked_when_that_checkout_is_absent asserts no phantom-artifact ANYWHERE in the store - so one bad entry reds your own pack, and would red every other PR in the repo if it landed on main. Grep your own record's artifacts block against `git ls-tree origin/main` plus your own diff before pushing."
  - "That same test is ENVIRONMENT-COUPLED and cannot be trusted locally: it asserts a negative over the whole store's output, so it reds (a) wherever a sibling checkout RESOLVES that CI lacks - a real mastermind/ clone makes a cross-repo entry checkable and phantom - and (b) in a SPARSE worktree, where data/ site/ verify_shots/ entries are omitted-but-tracked. Both produced a false local red here. To emulate CI: MACRO_MASTERMIND_REPO=/nonexistent MACRO_TERMINAL_REPO=/nonexistent, and treat any remaining phantom under a sparse-omitted dir as an artifact after checking it is tracked on origin/main."
  - "A NEGATIVE assertion is satisfied by a wrong subject name. 'X is never called', 'X is absent', 'no X' all PASS when X does not exist, while a positive assertion fails loudly on the same typo. Audit prose is where phantom names come from, because an auditor writing English invents a plausible verb without owning the symbol - quoting the audit faithfully is how the phantom reaches a frozen spec. Resolve every backticked identifier in a spec before freezing it, and label each miss NOT-YET-MINTED (a dispatch preflight) or NOT-A-SYMBOL (a defect); a lane cannot tell them apart and both look like green."
  - "The worktree-isolation guard refuses a heredoc combined with a run, git -C pointed at a runtime-computed path, and gh calls whose jq text it cannot verify. Working pattern: write a script file, then run it as a separate plain command."
  - "CLOSED THE SAME DAY BY WAVE 7 - this entry is kept because a lane may inherit the wave-6 version of it, and the correction has to be findable at the sentence that said it. ALL 40 rows now carry a subject-level measurement and NO row explains its status by whether a task has landed; the apply script asserts that the owning-task boilerplate survives nowhere. Six more rows moved (MGD-05/24/27/28/29/30), twelve of forty in total. Superseded text follows: The remaining 23 NOT_RUN rows still carry TASK-LEVEL notes ('owning task <T> has not landed'). They were not re-measured and must not be read as subject-measured - the ledger says so explicitly in scope_of_the_2026_09_27_subject_reaudit. Six of the nine rows that WERE measured moved, so the prior of a task-level note being wrong is not small."
  - "A delivered test whose DOCSTRING names an obligation may not pin it. test_internal_transfer_keeps_elimination_sign carries an MGD-19 docstring and calls the helper `composition._signed_value(...)`; its own comment concedes the casebook exposes no internal-transfer row. The ledger's status_is_never_inferred_from_a_test_name rule protects against the NAME; nothing protected against the DOCSTRING until R-MIN-36."
  - "An independent Opus audit was commissioned for the seven T03 rows and returned NO verdict at its 24-turn limit - the third such no-delta reviewer cycle in this program. Root cause was MY routing error: a status adjudication is ROUTE judgment, which the registry makes main-loop-only. Do not respawn a reviewer for an adjudication; inline the measurements and decide in the main loop."
---

# GMI Mining M1 integration — 2026-09-27 (wave 4 records)

**T04a is delivered, merged and proven.** PR #7950 merged `aff8b76cba6` at 2026-09-27T03:33:28Z
on concluded-green, and Audit B's frozen GREEN gate re-run against `origin/main`'s own bytes gives
**53 passed**. That closes the critical path that had been open since 09-24.

**The session's other outcome was a retraction.** Records PR #8060 had been merged 37 minutes
earlier under CLAUDE.md's docs-only `--admin` exception, on a diagnosis that ci.yml structurally
cannot schedule pack checks for an `agentos/*.md` diff. Measurement refuted it: `ci-plan`
**computes** the pack set from the changed files, took 3m56s, and planned a **reduced** set
(`contract-delta`, `ci-pack-0`, `ci-pack-1`) — all three `in_progress` at the merge. The operative
cause was not a CI subtlety but a stale read: the seat read the rollup at ~02:30, **pushed a new
head at 02:33:16Z** (ci.yml fired 16 seconds later), and merged at 02:56 without ever looking at
the run its own push created. A merge decision inherits the freshness of its evidence.

Three things follow, all landed here rather than left as notes. The wrong rule was **retracted at
source** — R-MIN-33g amends R-MIN-33f, whose shipped text told every future lane to read
`pending == 0` as green once the expected pack set is PRESENT, a rule that is both unsatisfiable
on a small plan and silent about re-reading after a push. The contamination was **bounded by
measurement**, not by assumption: #8053 merged on a run already concluded `success`, so the defect
is isolated to #8060. **RESOLVED 2026-09-27 04:2xZ — the run concluded FAILURE and main is NOT red;
the "reds therefore main is red" half of this paragraph is WITHDRAWN (see the verified entry above).**
What remains true is the isolation finding. Superseded text follows: watcher `byclvs37e` follows run
`36288860409` to conclusion, and if it reds, main is red from this seat's merge and this seat owes
the heal.

**Dispatch position is unchanged and worth stating plainly, because two successive handoffs got it
wrong in opposite directions.** #7950's merge unblocks no plan TASK. R-MIN-05 orders
`T01' → (T02 ∥ T04a) → T03 → T04b → T07`; T03 needs both #7950 merged **and** T02 delivered, T04b
comes after T03, and T02 itself waits on another seat's #7905. What #7950's merge actually
unblocked was this records lane, which had been deferred only because tabling a ruling required a
push to #7950 while its proof was in flight.
