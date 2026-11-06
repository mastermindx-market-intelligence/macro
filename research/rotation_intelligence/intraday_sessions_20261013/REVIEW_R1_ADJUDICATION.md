# Independent M2 Fabric review: adjudication and remedy

Original operation: rotation-intraday-session-research-20261013; Macro PR #9196. Original child rotation9196-semantic-review-r1 is now TERMINAL, rc=0, signal=ok, delivered. Root and parent match the original operation. The retained 267309-byte result has SHA256 745071e6cf61bf8637bc9a7b01f265dc38ed9b7d55210dbea0a6e375c09e4837. Its exact final verdict is retained separately; the full tool transcript is not duplicated in Git.

The subject was predecessor d5e076c247d993fe39b8ad9b9ef89b4ff80ff9f0, not the latest candidate. No approval is inferred from worker completion. The reviewer reported NOT PASS.

## Findings

B1 (accepted, blocking): minute-only rendering hides a seconds-long source interval. Reproduced with forty seconds and one millisecond. The actual grounding consumer now emits full UTC source stamps (seconds/fractions), measured seconds, and the benchmark's actual return.

B2 (accepted disclosure defect, causal overstatement rejected): allowed member endpoint skew was dropped by the consumer. It now retains and prints the allowed skew per endpoint and labels the time span as the SPY window. A flat member and a rising SPY genuinely differ in return; the review's statement that the entire relative result is manufactured solely by time mismatch is not established by that example. Bounded asynchronous comparison remains an approximation and is disclosed, not called exact synchrony.

B3 (already repaired after reviewed predecessor): the current consumer enforces the existing 45-minute source-age budget, same-session/calendar and arithmetic checks. The producer may retain a correctly dated historical observation, but stale evidence does not enter current intraday grounding. No new freshness policy or alert authority.

The review's generic sidecar-publication observation does not prove anonymous access: a filesystem directory named public is not an authentication receipt. The ordinary product still excludes the raw comparison baseline. Existing path access policy and production proof remain separate requirements; no route or credential is changed by this remedy.

Low-severity findings on absolute-magnitude display order and diagnostic omission are not new predictive ranks or release blockers for this descriptive slice. Stored-price tampering is not fixed by an unsigned self-generated checksum; the existing source writer/access boundary remains the trust owner.

## Review quality / execution scope

The reviewer exceeded the requested text-only/no-network analysis scope by locating repository copies and executing synthetic harnesses. It also reported an incidental Git background repack; its transcript reports completion and clean unchanged source heads. This is recorded, not silently accepted as scope compliance. We consume the reproducible useful findings but leave the original task NOT_ACCEPTED; no positive quality verdict or subject approval is fabricated. There is no active original reviewer left to duplicate. Follow-up review has a new bounded ID, retains original root/parent, and must use the frozen repaired source.

## Verification and next phase

Test-first: three new rendering controls failed on 8c7012e9461a. The amended eight-module functional suite passes 528 tests. UTC millisecond rendering, forty-second duration, benchmark performance and per-endpoint tolerance all travel through the actual consumer. Existing stale/correction/closing-path controls remain green. One existing pytest cleanup permission warning is retained; the tested source files have no permission change.

Direct remedy reason: CRITICAL_PATH_SHORTCUT, a small deterministic consumer edit under principal adjudication. UI work next uses the same Sector Intelligence page and existing pulse fetch, not a second data or scoring owner. Final source review and new-head hosted checks remain necessary before merge. No deployment, financial edge, live alert, overnight trajectory or production-user proof is claimed.
