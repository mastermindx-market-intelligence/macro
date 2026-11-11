# MACD replay: historical panels and observed producer output

## Capability and scope

The MACD/Prophet programme remains PARTIAL. This wave repairs two measurement defects in the existing replay path: sparse checkout must not replace available historical panels with later history, and an old reference file must not count as freshly produced output when the builder did nothing. A smaller provenance-label defect is repaired in the same panel path. These changes neither rerun the market studies nor qualify a trading rule.

Source carrier: Macro PR #7177, `sol/macd-cycle-research-20260915-c3`, starting at `9513a4d9353362c6e02fe56a402008f49b44b049`. The existing owned managed workspace and Remote Desktop Commander/Mac Studio carrier are unchanged. The initial repair loaded Mastermind `5ee11ab1e993616f3568cfca4069cb21fa61fd8f`. This resumed continuation loaded compatible INDEX and all required companions at protected Mastermind `4537f066775c73d305f82acf0643701f01f5e53c`; their procedure bytes are unchanged. Current live Chairman direction authorizes continued in-scope research/source repair, not release of trading or production authority.

The exact initial-head GitHub `contract-delta` check now passes; larger trusted CI packs were still queued at observation. The wave did not redispatch, cancel, waive, or take ownership of the shared CI infrastructure. Independent review and exact-head release acceptance remain separate.

## 1. Missing historical wide panels

Five synthetic failures demonstrated the gap left after the ticker-input repair. When a tracked historical wide panel was absent locally, later data could replace its historical rows and stock membership; a later-deleted panel could disappear entirely; corrupt pinned history could be bypassed with later valid values; and restoration provenance was absent.

Ticker and wide-panel restoration now share the existing pinned-input helper inside `prepare_reconstruction_tree`. Historical Git presence is checked before later or auxiliary fallback. Required unavailable/corrupt historical data refuses; historical rows and columns are preserved; only the missing permitted tail is appended. Full and sparse synthetic Git checkouts now traverse the same real two-pass builder pipeline to the same expected final board, with historical restoration recorded only where it occurred.

The genuine absent-at-vintage substitution case remains supported and disclosed. One older fixture had mistakenly committed its supposedly absent historical panel; it now commits historical constituents first and the later panel separately, retaining all constituents-diff assertions. A subsequent fixture-stage error was caught and corrected by explicitly staging the historical constituents before that first commit. Neither failed run is represented as a pass.

A separate test reproduced an inaccurate note: a panel loaded from a later Git revision was labeled as a gitignored auxiliary-checkout input. That note is now used only after an auxiliary file was actually read. The underlying substitution disclosure remains unchanged.

## 2. A zero-exit builder must actually write an output

The recorded synthetic `python -c pass` probe was accepted by the former `build_board` because a correctly stamped reference file already existed. The accepted cache bytes and original file modification time were unchanged. This is a reproduction of a no-output false-green, not a measured explanation of the historical 0.5769 disagreement.

The repaired owner keeps the old board available for legitimate input reads and observes its file state before and after the subprocess. A successful process leaving the old file untouched refuses. A legitimate same-content rewrite can pass because its write is observable. Invalid JSON, non-object output and wrong-date output do not earn a successful output receipt.

This is a file-write witness, not an adversarial attestation that every model calculation succeeded. A process that intentionally rewrites old content is not distinguishable solely by this witness. Historical input closure, semantic correctness and scientific validation remain independent obligations.

## 3. Reuse a witnessed cache, not an unexplained file

A companion `.buildproof.json` belongs to the existing temporary board cache, not a new authority or data store. It binds the originating output hash and write observation to the declared historical source, price fingerprint, vintage root, command digest and applied-pin digest. Unknown source/price identity disables reuse. Legacy bare caches, altered output, invalid proof, changed source, changed command and changed pins require a fresh build. Raw command bodies or secret environment values are not recorded in this companion.

The same final harness receipt now carries `board_builds.control` and `board_builds.replay`, each distinguishing `fresh` from `cache`. Cache reuse restores the validated output bytes to the real vintage consumer path, including a missing destination directory. The existing cache-coherence tests now seed their cache through a real first build whose command would fail if invoked twice; they retain both original consumer assertions rather than accepting an unproved hand-written cache fixture.

These bindings do not certify all nonprice inputs, installed dependencies, runtime clocks or publication eligibility. The receipt names that limit. They also do not grant merge, signal, forecast, rank, sizing or trade authority.

## 4. Earlier verified candidate and real synthetic execution

The earlier combined command was the existing CI-owned three-suite command: `python3 -m pytest tests/test_prophet_pit_replay.py tests/test_prophet_pit_replay_alpha_result.py tests/test_prophet_pit_replay_sparse_inputs.py -q --tb=short`, with an isolated owned basetemp and JUnit output. Native process 91837 completed with exit 0: **226 passed in 132.00 seconds**, versus the prior 199 cases. No additional test file or CI waiver was introduced.

Earlier replay source SHA256: `797d3cd22f68895d0bbba70bba1ca12644aa566cf8b848d61af77ffd3de23d05`.

The original five wide-panel cases failed before their repair. The no-op/bare-cache tests failed before the output guard; new receipt/cache-interface tests failed before that interface existed. The source-identity and provenance-label negative tests also failed before their fixes. The two real pipeline receipt tests separately failed when their builder evidence was not yet carried to the final receipt. Complete final results and bounded RED evidence are published alongside this report.

The full and sparse acceptance cases use temporary Git histories and **actual builder subprocesses** through input preparation, control, replay, board identity and final receipt construction. Both produce the same expected final fixture board, control agreement 1.0 without waiver, historical membership preserved, no plan mint, original source panel untouched, and distinct fresh/cache observations on the first/repeated run. That 1.0 is synthetic fixture agreement, not the real historical control and not a trading statistic.

The no-op pipeline cases prove refusal before `board_fidelity` is reached, including when the existing low-fidelity option is requested. The old reference remains intact; no successful build companion is minted. The same-content rewrite case remains valid, so refusing a no-op does not require deleting legitimate historical input.

## 5. Resumed continuation: historical tails must precede later revisions

The failed chat turn left more completed work on disk than its visible transcript showed. The saved producer/panel candidate was read back, its prior RED/GREEN evidence reconciled, and its current source `1dee7d141b5634b1e2da0c2b5d80fc0ffb1aaa96987ef2b542068bdff7ec23a8` freshly passed 229 tests in process94436. The older 226-test receipt above is retained as earlier evidence, not reused as verification of a different source. No pending source-writing process was found by the scoped process inspection.

A new two-pass adversarial fixture then failed in all four declared ticker/wide × revised/deleted-source cases. The control pass retained July14 and truncated the pinned source's July15 row. The replay pass read July15 from a later revision: the observed synthetic result was [100,901] instead of the pinned [100,101]. When the later source deleted the file, July15 disappeared. These are synthetic source-precedence failures, not real market returns or a demonstrated cause of the retained historical board disagreement.

The existing pinned restoration helper now also restores a shortened file's missing historical tail before applying later data. Already-present rows remain intact; pinned rows lost by control truncation are recovered from their original revision; only the genuinely later tail comes from the later source. Original-history deletion in the later revision cannot erase those pinned rows. Empty control windows are covered too. Per-file provenance and the existing final receipt identify historical-tail restoration separately from later-session additions, and totals count each changed file once.

The real-subprocess full/sparse fixture now consumes the entire restored history: its final AAA close is102 and its history sum is303, rather than accepting the final close alone while an intermediate row could be901. It checks identical full/sparse output, unchanged source panels, zero plan minting, correct final receipt, historical-tail provenance, and fresh-versus-cache behavior. This fixture agreement is not a live historical fidelity result.

A recovered exploratory test had expected a new refusal on an already-present corrupt local panel. That is not this patch's contract: existing unreadable-file handling remains unchanged, preserves the corrupt bytes and reports the unreadable input; it does not substitute later valid history. A missing or shortened input that requires unreadable pinned history still refuses. The exploratory failure and the corrected contract test are both retained; no failure is relabeled as a pass.

## 6. Release and scientific boundaries

Current source before release verification: `6cb1798216fd6c81b4c61c08f91dd634d28434c7bd45e3cf61d17f7b9cb3ee3e`. The final exact-source verification and receipt checks are in `replay_sparse_panel_repair_20260916_r4/verification.json`; earlier receipts remain historical evidence.

Current-main comparison at `0fa09ade7ef485935860866ff3342a7492b550d4` finds unchanged governing agent/replay/contract-checker sources. The owning replay CI job differs only by this PR's previously published enrollment of its two new suites; unrelated main CI changes are not adopted or reverted here. No shared CI run was cancelled or redispatched.

This remains the same source carrier and managed workspace. Direct-work rationale: PRINCIPAL_JUDGMENT for source-precedence and misleading-output interpretation, CRITICAL_PATH_SHORTCUT for completing the interrupted bounded repair. No new Executive Job, worker, provider session, replay system or forward ledger was created.

The real control remains0.5769 versus the unchanged0.85 floor. Its original transient input bodies, runtime/source/publication clocks and independent scientific review are still required; the separately blocked security-input and archive inspections were not retried or reconstructed. No live rank, entry, size, plan, trade or probability is changed. Preserve all completed MACD/holding/exit/benchmark and adverse archived-score studies.

Next release action: publish this exact tested candidate on draft PR7177, consume independent source review and applicable exact-head CI, and keep HOLD-FOR-SOL until its stated release gates clear. Next scientific action: qualify original inputs through their existing owners once the inspection gates are lawfully clear, then run the same canonical historical control without a waiver. Source correctness is a dependency, not acceptance of a Prophet upgrade.

## Final resumed source result and packaging boundary

The exact candidate completed the existing three-suite command in process15113 with exit0: **237 passed in53.69 seconds**, including historical-tail provenance, one-file session accounting, full/sparse subprocess output, no-op rejection and valid cache reuse. The final source and test identities are in `resumed-final-source.json`; the original completed run log and JUnit file are `resumed-final.log` and `resumed-final.xml`. Replay source SHA256 is `6cb1798216fd6c81b4c61c08f91dd634d28434c7bd45e3cf61d17f7b9cb3ee3e`.

Evidence packaging process21038 stopped at its assertion that exactly two fixture evidence paths were found, after copying the completed logs and preserving the earlier verification receipt. A subsequent inspection of those fixture paths was platform-blocked. That inspection was not retried, split or rerouted. Its later planned fixture-copy and handoff-update steps are not claimed complete. The existing `pipeline_full_fixture.json` and `pipeline_sparse_fixture.json` remain evidence for the earlier candidate named in `verification_before_resume.json`, NOT the current source. Current full/sparse correctness is established by the completed tests and their assertions, not by those older fixture copies or an uncompleted extra inspection.

The latest `verification.json` explicitly records this boundary and points to the completed exact-source test run. Source publication and independent review may proceed under their own gates; the blocked inspection and all earlier real-data inspection restrictions remain held. Local test success is not concluded remote CI, original-market reproduction, scientific acceptance or production proof.
