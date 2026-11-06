# Options Context Audit preregistration v2 charter: independent review record

- **Reviewed:** `research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md` at Macro `main` pin `01f86f7d7431` (charter blob `4f321e614a6adf48`; merged by PR #7711 as `d1b93722ec41` and edited in place since). It was read together with the following, all as staged at the pin: `agentos/workstreams/WS-OPTIONS-CONTEXT-AUDIT-PREREG-V2.md`, the two decisions that WS record cites, the 2026-08-13 ledger-bound adjudication, `sparse_selector_preregistration_receipt_v1.json`, the v1 context engine, receipt store and auditor sources, and the audit service unit.
- **Reviewer:** an independent Claude Opus auditor (ROUTE: AUDIT, MODE: READ_ONLY), commissioned by the Fable Options Intelligence seat. It is not the charter's author, owner or acceptor, and it made no edits.
- **Date:** 2026-10-22.
- **Verdict:** `REPAIR_REQUIRED`. The charter is not accept-eligible at pin `01f86f7d7431`. The audit found 2 BLOCKER, 10 MAJOR and 4 MINOR findings; check B (constraints already broken at the pin) found none. The seat recorded the verdict and did not accept the charter (D89).
- **Acceptor finding:** the charter names only a "commissioning seat" (l.3, l.192, l.223). The WS record (l.35–38) and `DEC:PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2` (l.18–19) name Sol's acceptance as the implementation gate, and no delegation record exists. The acceptor is Sol, or a recorded delegation. The repair owner is the WS owner `coo-fable`.
- **Records:** `DSC:OPTIONS-CONTEXT-AUDIT-V2-ACCEPTOR-IS-SOL-NOT-SEAT`, `DSC:OPTIONS-CONTEXT-AUDIT-V2-TEST3-IS-UNSATISFIABLE`, `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2`.
- **Not changed by this record:** the charter and the WS record. Nothing here accepts, amends or implements the charter.
- **Reading the packet:** line numbers refer to the copies staged at the pin. The staging directory named in the packet is not durable. Short names map to repository paths as follows:
  - CH = the charter above.
  - WS = `agentos/workstreams/WS-OPTIONS-CONTEXT-AUDIT-PREREG-V2.md`.
  - DECW = `agentos/decisions/DEC-W2C-V1-CONTEXT-OWNER-DECOUPLED-FROM-OPTIONS-AUDIT.md`.
  - DECP = `agentos/decisions/DEC-PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2.md`.
  - DSC = `agentos/discoveries/DSC-OPTIONS-CONTEXT-AUDIT-V1-TIMEOUT-PRECEDES-4096-REFUSAL.md`.
  - ADJ, SSR, CTX, RS, AUD and UNIT = the paths listed in the packet, without the `src/` prefix.
  - PIN = the seat's staging pin manifest (not in the repository).

## Audit packet (verbatim)

**VERDICT (seat packet): PARK.** Do not accept the charter in D89 as written.

**VERDICT: REPAIR_REQUIRED**

**WHY OPUS:** The defects that decide this are contradictions across documents, not missing facts. Charter l.74/l.192 conflict with WS do_not_redo and both DEC records. Test 3 conflicts with the receipt fields at l.130–131. Authority attribution splits across three records. A false ACCEPT would ratify a path, opened by the seat alone, to reopen the byte-pinned v1 bounds.

All files are under `/private/tmp/claude-501/-Volumes-Mastermind-agent-workspaces-claude-5600d31ffa29643a-options-intelligence-e2e-c62b5a-a093ccd8fc6d20f2/f77d3f70-78e4-4d1b-8664-d2f9b27233ea/scratchpad/wsv2/`. Short names used below:
- CH = `OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md`
- WS = `WS-OPTIONS-CONTEXT-AUDIT-PREREG-V2.md`
- DECW = `src/agentos/decisions/DEC-W2C-V1-CONTEXT-OWNER-DECOUPLED-FROM-OPTIONS-AUDIT.md`
- DECP = `src/agentos/decisions/DEC-PRODUCTION-RECORDS-ROW-BOUND-STAYS-FAIL-CLOSED-UNTIL-PREREG-V2.md`
- ADJ = `src/research/options_estate/OPTIONS_CONTEXT_AUDIT_LEDGER_BOUND_ADJUDICATION_2026-08-13.md`
- SSR = `src/research/options_estate/sparse_selector_preregistration_receipt_v1.json`
- CTX = `src/engine/options_market_memory_context.py`
- RS = `src/engine/options_market_memory_receipt_store.py`
- AUD = `src/scripts/audit_options_market_memory_context.py`
- UNIT = `src/app/deploy/macro-market-memory-options-context-audit.service`

## FINDINGS

**1. BLOCKER: the staged files do not make the Fable seat an eligible acceptor (check G).**
- The charter names only an unidentified "commissioning seat": CH l.3 "PENDING SEAT ACCEPTANCE", l.192, l.223 "binds only once the commissioning seat accepts it".
- The WS names Sol: WS l.35–36 "still gated on Sol accepting the preregistration"; WS l.38 "Sol acceptance of the preregistration charter … is the implementation gate".
- Fable's own DEC, written under the Chairman's 2026-10-11 autonomy directive, still reserves acceptance to Sol: DECP l.18–19 "Sol's acceptance of that preregistration remains the implementation gate", l.45–46, decided_by coo-fable l.60.
- `owner: coo-fable` (WS l.16) makes Fable the workstream owner, not the acceptor. DECW is decided_by ceo-sol (l.59).
- No staged file equates "commissioning seat" with Fable or records a delegation from Sol to Fable.
- Consequence: a Fable ACCEPT contradicts Fable's own DECP. It would also be the seat approving a sizing proposal its own programme put forward ("proposed for seat acceptance", CH l.76). DECP l.24–25 calls a seat-chosen capacity claim "precisely the self-excuse the gauntlet exists to stop".

**2. BLOCKER: CH l.74 and l.192 let the seat reopen byte-pinned v1 bounds by recording a DEC.**
- CH l.74: "Whether any of these bounds moves is a preregistration contract decision for the commissioning seat, recorded as a `DEC:` record." Item 1 of that list is v1 `_MAX_REFERENCES` (CH l.70).
- CH l.192: "reopening one requires a material invalidator recorded by the commissioning seat."
- This breaks:
  - WS do_not_redo l.55 and l.54, which have no reopening clause.
  - DECW l.31–34: lifting the ceiling "is a preregistration act, not a buffer change".
  - DECP l.18–19: the seat "does not pick a new constant".
  - ADJ l.197–203: raising the constant in place is "Not available"; it trips `global_abstain_new_version_and_future_nyse_boundary_required`.
  - The charter's own CH l.24 and l.121.
- Consequence: acceptance ratifies a second change-control path alongside SSR `version_fence.rule_change_policy = new_version_and_new_forward_cohort`.

**3. MAJOR: CH l.78–80 can be read as satisfying DECP's reversal condition.**
- CH l.78: "The stale 25,000-row / 48 MiB figure is replaced by a stated envelope." CH l.80 gives explicit numbers (118,036 rows / 183,931,496 B).
- Together these look like "states the new bound, its measurement basis, and its headroom" (DECP l.65–66).
- This contradicts CH l.162 ("Numeric limits … not chosen in this charter") and DECP l.12–19.
- `market_memory_production_records.py` is not in WS owns_paths (l.20–25), so no v2 artifact can resize MAX_SOURCE_ROWS. The gate is circular: DECP points to the charter, the charter (l.74) points back to a seat DEC, and DECP says the seat won't pick one.
- Consequence: an ACCEPT could be cited to raise MAX_SOURCE_ROWS=25_000 or the auditor bound (AUD l.53–54) without any benchmark. That is exactly the alternative DECP rejected at l.33–37.

**4. MAJOR: acceptance test 3 cannot be satisfied as written.**
- The receipt must bind the run manifest ("run digests, run count", CH l.130) and the observed "peak RSS, CPU seconds, wall seconds" (CH l.131).
- Test 3 (l.208) and l.143 nonetheless require identical receipt bytes across chunk-size changes, run-partition changes and replays.
- Test 3 also requires "input reorder" to give identical output, while l.110, l.141, l.167 and test 4 (l.209) require reorder to refuse.
- Consequence: the child must reinterpret the preregistration to pass, which is the in-place reinterpretation ADJ l.189–193 forbids. Any correct replay would also trip REPLAY_MISMATCH (l.176).

**5. MAJOR: a v2 that refuses everything passes the acceptance contract.**
- No test requires a successful receipt on the current corpus under the real service class.
- l.81 allows any declared ceiling. l.82 makes refusal past the ceiling compliant.
- Test 6 only requires that limits are "enforced". Test 2 bars only an "empty result", and a refusal is not one. Test 1 accepts a "refusal reason" for every row. Test 8 holds trivially when nothing is published.
- The l.204 preamble makes "acceptable" a review of the source head only, with no live receipt required.
- Consequence: this contradicts WS l.5–9 ("can represent the live owner corpus … with stated headroom"). A permanently refusing v2 could be called "accepted".

**6. MAJOR: the fixed resource budget becomes a closed decision with no evidence it is feasible.**
- The budget is wall ≤150 s at CPUQuota 50%, i.e. ≤75 CPU-seconds (CH l.185, l.83 "the budget is not [the child's]", l.195, l.192).
- Production evidence: v1 spent 90.134 CPU-s at 3,897 rows and did not finish (DSC l.21–26). DECW l.19–20 attributes that CPU to the audit.
- The charter's local benchmark leaves out context-store resolution (CH l.96, l.219). That is the per-episode stage AUD l.322–327 performs.
- v2 must handle at least 29,517 owners (CH l.70), and the fixture is 4× that (l.80).
- WS l.54 only bars raising limits "as a substitute for v2". The charter extends the prohibition to v2 itself and adds MemoryHigh/MemoryMax.
- Consequence: acceptance may lock in a contract the corpus cannot meet, with only the seat-level reopening path from finding 2 as an exit.

**7. MAJOR: the campaign path guarantees a refusal on the live corpus, and the fix has no owner.**
- CH l.51 and l.100 require CAMPAIGN_OUTPUT_STALE / CAMPAIGN_REPLAY_MISMATCH "until a separately accepted campaign contract resolves them". No owner or record is named for that contract.
- The campaign-v2 artifacts did not change between the design SHA and the refresh: same sha `0c242957…` at l.37 and l.63; same rows/bytes at l.43 and l.64. Over the same period episodes tripled.
- The stale-campaign census (8,872 / 769) was not refreshed, and `checkpoint.json` (manifested at l.48) is missing from the refresh table (l.57–64).
- v1 avoids the replay mismatch only by slicing its inputs at CAMPAIGN_RULE_FROZEN_AT (AUD l.202–250, l.328–338). The charter's algorithm description (l.87–94) omits this step, and its no-truncation rules (l.178, l.196) leave it unresolved for v2.

**8. MAJOR: incremental generations conflict with the completeness requirement.**
- CH l.83 allows "each run's work bounded by the appended suffix".
- CH l.98 requires every governed row to be "read, parsed, identity-checked" on each run. l.113 requires the complete reference set.
- The charter never says whether a HEAD produced in incremental mode contains all references.
- Consequence: a suffix-only HEAD makes older owners resolve as `exact_requested_as_of_context_absent` under the konseki binding (ADJ l.140–151). That is owner eviction by construction, which the DNR forbids.

**9. MAJOR: the charter does not bind v2 into a registration or say how it succeeds v1.**
- SSR appears only as the pin at CH l.194. There is no new selector registration, no konseki `contract_receipts`, no `head_schema`, and no `build_options_sparse_selector_prereg.py`.
- ADJ l.243–245 ties v2's boundary to the selector's const fields.
- ADJ l.184–195 defines a larger-cap validator not pinned by the registration as the rejected "shadow".
- SSR konseki `head_schema` is still `…receipt_head/v1`.
- v1 stays "independent" (CH l.121) and keeps running (UNIT l.13; timer l.6).
- Consequence: test 7's "no second audit authority" (l.198, l.212) is either violated by v2's existence or unfalsifiable. This risks breaching WS do_not_redo l.58.

**10. MAJOR: the charter's binding list omits a do_not_redo item and other pinned caps.**
- Omitted: the receipt-store ceiling `0 <= count <= 4096` (RS l.403), which WS l.55 names explicitly.
- Also omitted: the h60 replay cap (CTX l.679), the 8 MiB per-artifact byte cap (CTX l.925) and the `capture_count` ≤4096 cap (CTX l.953).
- CH l.162 calls the 8 MiB cap "historical", but it is live in the pinned file.
- Consequence: the child's do-not-redo list understates what is pinned.

**11. MAJOR: the forward-cohort boundary clock is undefined, and "stale" is undefined.**
- CH l.145 "accepted on `origin/main`" blurs merged and accepted. v1 used an exact rule (SSR `effective_freeze_rule = later_of_registered_at_and_first_origin_main_commit_containing_exact_benchmark_digest`).
- CH l.145 also defers the freshness clock and stale-source policy to the child.
- Consequence: the start of the cohort reset is ambiguous, and test 5's "stale" cannot be checked yet.

**12. MAJOR: the 2026-10-11 additions have not been independently reviewed.**
- The review section (CH l.215–221) predates the capacity refresh and envelope (l.53–83), "refusal before kill" (l.181–188) and the test-6 extension (l.188, l.211).
- DECP l.30–31 requires the bound to be sized "under review".
- Consequence: accepting now ratifies sizing that has had no review. This audit is the first review of that material, and it found defects.

**13. MINOR: acceptance must bind the exact charter bytes.** The charter has been edited in place (CH l.14; WS l.32–34). The design SHA (l.12), refresh SHA (l.55), merge `d1b93722ec41` and pin `01f86f7d` all differ. An acceptance that does not bind blob `4f321e614a6adf48` (PIN l.5) lets later edits ride on it.

**14. MINOR: provenance gaps.**
- The production-host refusal is asserted without journal evidence (CH l.72; DECP l.51 cites only "ORCH-OPS read-only census").
- The figures are origin/main blobs, not the host's `/opt/macro` data (UNIT l.12–13).
- The newest episode is 2026-09-25 in a 2026-10-11 measurement, and the gap is not explained.
- WS l.41 turns five data points into a present-tense rate, although CH l.66 says "not a forecast".

**15. MINOR: the service sandbox is not addressed.**
- The external-sort temp runs (CH l.111, l.158) have no stated location. The unit has PrivateTmp (UNIT l.25), ProtectSystem=strict (l.28) and a single ReadWritePaths (l.46).
- CH l.183 also omits CPUWeight=20 (UNIT l.16).
- From cgroup semantics (external to the staged files): the RSS budget in l.185/l.187 is not the memory MemoryHigh actually counts, so the "no throttle" check in l.188 may fail for reasons the budget does not measure.

**16. MINOR: stale motivation.**
- CH l.183 restates DSC's "timeout precedes the 4,096 refusal" as current.
- At the refreshed corpus, v1 reads episodes first (AUD l.274) and refuses at l.170–171 (29,509 > 25,000) before any construction. WS landmine l.61 is stale for the same reason.
- Also, WS l.29 marks the charter wave "done" while CH l.3 says "PENDING".

## FALSE-ACCEPT RE-COUPLES
- **v1 ceiling edits by seat DEC** (CH l.74, l.192). This would move CTX l.43, l.675–680, l.925, l.953 and RS l.403. All of these are pinned by SSR `konseki.contract_receipts` (`7d3b410f…`, `923d9d61…`). Editing them causes a global abstain (ADJ l.197–200).
- **Raising MAX_SOURCE_ROWS=25_000 and the auditor's AUD l.53–54 to envelope numbers.** The route is CH l.78–80 combined with DECP l.65–66. DECP l.33–37 already rejected this.
- **A larger-cap validator with no registration** (finding 9). This is the shadow ADJ l.184–195 rejects, and it risks breaching WS l.58.
- **Suffix-only HEAD** (CH l.83). This produces owner-absent nulls (ADJ l.146–151), i.e. DNR eviction.
- **Implementation-child admission.** WS l.35–38 makes acceptance "the implementation gate", while the pre-implementation definitions (CH l.145) do not yet exist.
- **Recoupling into `macro-market-memory-context.service`:** none found. CH l.199 forbids it, and UNIT l.7–8 has only `After=`.

## NONE-FOUND
- **B (constraints already broken at the pin):** none.
  - Grepped `_MAX_|MAX_|25_000|4_096|4096|ceiling|limit` in CTX, RS and AUD; read UNIT l.1–76 in full.
  - `_MAX_REFERENCES = 4_096` at CTX l.43. UNIT values match: TimeoutStartSec=180 l.14, CPUQuota=50% l.17, MemoryHigh=256M l.18, MemoryMax=512M l.19, Nice=10 l.15, IOWeight=20 l.20.
  - AUD 25_000 / 48 MiB at l.53–54. The legacy campaign 8 / 10,492 / `db326f5c` at AUD l.56–60 matches CH l.34.
  - PIN l.6–7 hash prefixes equal the SSR-pinned sha256 values for CTX and RS.
  - The arithmetic at CH l.39, l.70, l.71, l.80 and l.81 reconciles, and every 64-hex digest has the right length.
  - Not verifiable: `market_memory_production_records.py` is not staged.
- **A (charter recoupling):** none. Grepped `deploy|install|enable|timer|unit|Requires|Wants|PartOf` in CH (hits only l.187, l.195, l.225) and read UNIT in full.
- **E (deployment, install or unit edit authorised):** none beyond findings 3 and 9 and WS l.38. CH l.24 and l.225 disclaim all of these.

## Check C: can each acceptance test fail on a wrong implementation?

| Test | Can it fail? | Wrong implementation it catches | Gap |
|---|---|---|---|
| 1. Coverage | Yes | Drops one reference | The "refusal reason" clause lets a whole-run refusal pass |
| 2. Anti-vacuity | Yes | Empty output from a non-empty population | Does not catch universal refusal |
| 3. Determinism | Unsatisfiable as written | — | See finding 4 |
| 4. Correction safety | Yes | In-place edit or one-row shrink that still publishes | Correction-row format is undefined (CH l.102) |
| 5. Freshness/session | Partly | Backdated row admitted as prospective | Passes an implementation that marks everything retrospective; "stale" undefined |
| 6. Resource truth | Yes | No in-process wall budget (killed at 180 s with no record) | Passes a ceiling set below the current corpus |
| 7. Authority isolation | v1-bytes clause only | v1 byte change | "No second authority" is undefined (finding 9) |
| 8. Receipt integrity | Yes | Crash between object write and HEAD | Holds trivially when nothing publishes |

## Check F: open gates (l.215–225)

**Must close before acceptance:**
- Who accepts (l.223; finding 1).
- Test 3 repair, including the "interrupted writes" case named at l.221 (finding 4).
- Numbered tests for cross-file snapshot mutation and stale-checkpoint refusal. These are named at l.221 but are only prose at l.147 and l.51/l.100.
- Resolve test 6 vacuity (finding 5).
- Feasibility under the real service class before the fixed budget is closed (finding 6).
- Name an owner for the campaign contract (l.100).

**Belongs to the implementation child:**
- The l.219 and l.223 benchmark, and the numeric limits.
- Correction format.
- Benchmark receipt.
- The l.225 child admission. Its release criteria must be stated in the acceptance record.

## Check D: measurement provenance
- **Rows and bytes:** method and source are stated (CH l.55: newline count, blob size, commit `f8dc4bb0`).
- **Per-session growth figures (l.66):** derived from session_date; the bucketing method is not stated.
- **2026-10-11 date:** given in the heading only, not tied to the commit.
- **Headroom:** stated only as a fixture multiple (4×, about 39 sessions). No reason is given for 4×, and ADJ l.246–247 warns against "a larger arbitrary number". It is also not a required operating ceiling, because l.81 lets the implementation declare any ceiling.

**To unblock:**
- Amend CH l.74, l.78, l.83, l.192, test 3 and tests 5–7 as above.
- Record whether the seat holds the acceptor role.
- Bind the accepted blob.

**STATUS: COMPLETE.** Not covered because the files were not staged: `market_memory_production_records.py`, `macro-market-memory-context.service`, the DNR record, PR #7728, and the Skillpack.
