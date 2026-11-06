---
workstream: WS:LIVE-ENTRY-RADAR
# session/model/ended_because attribute the original Phase-1 return only.
# They do not declare that the continuing root session has ended or the parent mission is complete.
session: claude/rs-pullback-launch-phase1-20261007
model: sol
ended_because: blocked
mission: "Continue RS Pullback Launch through existing source owners, delivery and data admission; Phase 1 remains NOT_ADMITTED and the parent signal program remains incomplete."
# state_before and changed preserve the original Phase-1 attribution.
state_before: "Research complete at macro@21e7ece49b682d65a63f73ba6045853aded782f0; implementation not started."
changed:
  - path: engine/entry_radar/replay/rs_pullback_launch_data.py
    what: "Pure complete-minute input adapter and source-owner census evaluation; no detector or authority registration."
  - path: scripts/entry_radar_rs_pullback_phase1.py
    what: "Offline reproducible census/input-frame entrypoint, no live-source or ledger writes."
  - path: research/live_entry_radar/rs_pullback_launch/PHASE1_SOURCE_CENSUS_2026-10-07.json
    what: "Pinned source and read-only production inventory/qualifier receipts."
  - path: research/live_entry_radar/rs_pullback_launch/PHASE1_ADMISSION_2026-10-07.json
    what: "Reproducible NOT_ADMITTED verdict with 29 named refusals."
# verified/unverified/unresolved/next_actions describe the cumulative checkpoint below.
verified:
  - claim: "The original Phase-1 negative result and retention-v1 delivery are complete within their engineering scopes."
    command: "Macro #8571/#8581 and Terminal #840 delivery records; original Phase-1 artifact and installed 12-control retention receipt."
    result: "Phase1 SHA a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f remains exact: NOT_ADMITTED, 29 refusals, H1/H2/H3 NOT_TESTED and all authority false; retention proof is synthetic installed conformance, not a market pilot."
  - claim: "Calendar and Native source components have scoped installed proof."
    command: "Calendar #8602 installed 10-control receipt at 09:34:38Z; Native #8607 required CI 37609426098 and installed proof/lineage/delivery records from process 93607."
    result: "Calendar proof PASS. Native proof PASS at 11:56:09–15Z with exact 13-file bindings and positive release ancestry: MU bound, SPY/QQQ/SMH original refusals retained; no historical visibility recertification or Radar admission."
  - claim: "The v2 reader is installed at the hash/import level and Terminal v2 source has merged with exact postmerge identity."
    command: "Macro #8618 merge 67c1d8155d9194825f6cb301967d6b1c1f91b433 and 10:34 installed import/hash receipt; Terminal #843 CI 37609414595, merge e963eefb3ac1984008caae922d6f43bfafa9d827 and postmerge process 73169."
    result: "Terminal v2 all 10 required jobs passed; four accepted source blobs exact at squash. Normal producer deployment and the paired installed 19-control proof remain pending."
  - claim: "Split source delivery is merged, with installation proof prepared but not executed."
    command: "Macro #8625 required CI 37610310900; accepted d657ab26781e87a19d9c8705d5ac293c816acbb5; squash f2c33b5e1373a344fde232a6750ef479ccfd6331; postmerge process 13259."
    result: "Exact reviewed merge tree 2ce5b02de07fbb1a8ba4c8211b403e7d013fa256. Remote proof 62ab08fb… and wrapper 12992c28… independently reviewed; no installed Split result or factor applicability yet."
  - claim: "Raw-v3 candidates and eleven-case listing research have explicit remaining boundaries."
    command: "Macro #8623 required CI 37610526356; Terminal #844 integration 61800, retained failed browser 71984, passing browser 78787 and exact commit/push 85130; corrected LISTING_TRANSITION_RESEARCH_2026-10-07.md."
    result: "Macro raw-v3 remains DRAFT/HOLD until paired v2 proof. Terminal daily-axis case passed locally with actual consumer evidence; accepted capture blobs unchanged at a826c945d666f6f34d2dddcf72222568df4dbff3, hosted CI 37622577138 running. Original hosted and local failures retained. Eleven listing cases researched; no transition or later Native attempt applied."
  # Original Phase-1 verification entries remain historical evidence.
  - claim: "The CLI binds imports to this repository even when a foreign package precedes an ambient root."
    command: "python3 -m pytest tests/test_check_script_import_pinning.py -q; actual CLI invocation with hostile engine decoy and repo root later on PYTHONPATH"
    result: "11 passed; decoy not executed; CLI admission output byte-identical. Conditional pin repaired without baseline or waiver changes."
  - claim: "The corrected code-CI step passes all 30 RS conformance tests and 27 existing frozen-panel tests."
    command: "python3 -m pytest tests/test_research_price_panel.py tests/test_entry_radar_rs_pullback_phase1.py -q"
    result: "57 passed, 85 subtests passed after six independent review findings were repaired; unrelated existing temporary-directory cleanup warnings."
  - claim: "The actual source census does not support the commissioned market pilot."
    command: "python3 scripts/entry_radar_rs_pullback_phase1.py --census research/live_entry_radar/rs_pullback_launch/PHASE1_SOURCE_CENSUS_2026-10-07.json"
    result: "NOT_ADMITTED; 29 refusals; H1/H2/H3 NOT_TESTED; all authority false."
  - claim: "Existing deployed Terminal qualification was executed without source/data modification."
    command: "ingest.intraday_qualification.qualify_store on SPY/QQQ/SMH/MU 1m and SPY 5m; 2026-09-28 through 2026-10-05; cutoff 1791244800; as_observed; read-only process 61222."
    result: "Required 1m files missing; complete-grid SPY 5m control still has zero as-observed rows and pit_proven=false."
unverified:
  - claim: "Terminal v2 normal deployment and paired installed declaration/basis/framing conformance."
    what_would_verify: "Resolve the recorded host disk-full condition through its existing owner, verify normal deployment of the exact accepted producer, then run and retain the reviewed 19-control paired installed proof."
  - claim: "Installed Split owner function conformance."
    what_would_verify: "Observe normal installation of the merged Split source, establish exact positive release lineage and installed source closure, then execute the reviewed one-attempt wrapper and retain its actual result. Namespace-only loading and synthetic evidence cannot prove normal application integration or provider acquisition."
  - claim: "Raw-v3 source delivery and installed paired behavior."
    what_would_verify: "Complete Terminal #844 binding CI 37622577138 for the reviewed local browser repair, review any new current-main delta, then deliver Macro reader before Terminal producer after v2 proof is complete."
  - claim: "Listing-transition application and a later immutable Native attempt."
    what_would_verify: "Review and prove the existing owner's class/listing/observation-time extension, current-tip lookup and versioned attempt history; retain every original Native refusal and clock. Research filings alone do not qualify identity inputs."
  - claim: "A real immutable first-seen one-minute leader/pullback pilot can be constructed."
    what_would_verify: "Existing data owners supply retained 1m revisions with listing identity, qualified raw/split basis, calendar and actual daily/incumbent receipts; rerun Phase 1 on a complete pilot population."
  - claim: "Historical or prospective H1/H2/H3 edge."
    what_would_verify: "Admitted data, TrialLedger preregistration, strong B0 and controls/ablations, then prospective paired incumbent validation."
unresolved:
  - "At the supplied 12:24Z host census, /dev/vda1 had 77G used and zero available, updater fetch had failed after 11:51Z, and checkout remained f1966d3fdae3f14f42c8e026958f74590d72f9fe. No cleanup or manual retry success is established."
  - "Paired installed v2 conformance, installed Split proof and raw-v3 delivery remain pending; required source/CI/proof records must not be replaced by this checkpoint."
  - "Current Native delivery does not erase the original eleven lost-row transition evidence or upgrade SPY/QQQ/SMH refusals. No later Native attempt is admitted."
  - "Missing admitted 1m cohort/cadence/history, factor applicability and complete pilot/nonfire/failure population; the 4096-attempt cap is not a 90-session guarantee."
  - "Per-row stale daily context and missing faithful historical Entry Engine input/output receipts."
  - "No detector registration, calibrated probability, market-panel admission, or production signal authority."
next_actions:
  - "Root reconciles safe disk recovery through the existing owner; preserve the original updater failure and actual recovery result without speculative cleanup or blind retry."
  - "Complete normal Terminal #843 deployment after its exact postmerge verification, then run the reviewed paired v2 installed proof while the v2 Macro harness remains installed."
  - "Observe normal Split installation and execute the independently reviewed single-attempt wrapper; retain actual lineage, intent, raw output and scoped result."
  - "Complete Terminal #844 binding CI for accepted a826c945d666f6f34d2dddcf72222568df4dbff3, preserve failed attempts and accepted capture blobs, reconcile any new current-main delta, and deliver raw-v3 reader before producer after the v2 dependency."
  - "Review the bounded DOMO/HUCK and YYGH/YFOR existing-owner extension and later Native-attempt versioning; separately qualify actual permitted raw/split acquisition through existing owners."
  - "Bind daily/incumbent receipts and complete pilot population, rerun Phase 1 before baseline/outcome work, and continue toward the preserved total-program DONE_WHEN without widening authority."
do_not_redo:
  - "Do not rerun the completed broad research commission or eleven-case listing research merely because branches move; refresh only changed or unresolved evidence."
  - "Do not repeat the exact delivered Phase-1, retention-v1, Calendar or Native proofs without a concrete relevant change; recover their pinned receipts first."
  - "Do not substitute 5m history or corrected-history backfills for true 1m historical first-seen evidence."
  - "Do not duplicate Macro #7274/#7275, Fable Terminal #784 performance work, or Terminal #814 intraday route changes."
  - "Do not register a detector, write TrialLedger/shared ledgers, let C4 fire, use F1, or grant rank/gate/size/order authority."
  - "Do not reopen the operator-confirmed global licensing gate without new evidence, fabricate 90 sessions, or create another data/lifecycle/publication/scheduler/ledger owner."
danger_areas:
  - "Bar end is not publication/receipt time; Terminal ET display epochs are not true UTC instants."
  - "Synthetic conformance, a source merge, a health response and a current installed reader prove different things; none admits a market pilot or an edge."
  - "Fresh top-level daily publication does not refresh stale constituent rows."
  - "Current research and actual new reads cannot be backdated into historical identity or rewrite original REFUSED Native evidence."
  - "A response adjustment flag or separately fetched latest factor snapshot does not establish a shared basis vintage."
---

## Cumulative source and delivery checkpoint — 2026-10-07

**Parent `WS:LIVE-ENTRY-RADAR`; MISSION_COMPLETE: false. Phase 1 remains NOT_ADMITTED; H1/H2/H3 remain NOT_TESTED; all research/trading authority remains false.** The original Phase-1 return is complete through its permitted negative result. Later source components advance the continuing commission; they do not complete the parent program or admit the market panel.

This cumulative checkpoint includes Terminal #843 postmerge verification process 73169, Terminal #844 retained browser failure 71984, passing corrected browser run 78787, and exact commit/push 85130. Root observed the new required CI 37622577138 running at 12:41Z. The recorded 12:24Z disk census is a historical host observation; it is not a new current disk measurement. Subsequent bounded preparation includes independently accepted paired-v2 proof and read-only deployment budget assessment; neither establishes deployment. Root is continuing the concrete recovery and delivery work. The YAML `session`, `model` and `ended_because` fields retain attribution to the original Phase-1 return, not an assertion that the active root session ended. Machine-facing verification and continuation fields describe this cumulative frontier.

Current protected procedure pin: Mastermind `a2c93f1d5280f285751107543645154e9b20eb8f`. Root read the complete applicable procedures; the one-commit delta from `a2254b290caa7b422fd93657e44e992152541ca7` contains four unrelated ResearchReadMCP files and leaves these procedures unchanged. Earlier operations retain their original procedure attribution in the historical sections. This checkpoint does not change the wider WS-LIVE-ENTRY-RADAR C0..C8 queue or create a new session lifecycle or source owner.

### Delivered components and their exact limits

| Component | Delivery evidence | What remains outside the result |
|---|---|---|
| Original Phase 1 | [Macro #8571](https://github.com/mastermindx-market-intelligence/macro/pull/8571), squash `47a3a248ba9228b498376d2bdc170fd61e38dac0`. [Original admission](../../research/live_entry_radar/rs_pullback_launch/PHASE1_ADMISSION_2026-10-07.json) remains SHA-256 `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`: 29 named refusals. | No admitted pilot, detector or outcome claim. Preserve the original result. |
| Retention v1 | [Macro #8581](https://github.com/mastermindx-market-intelligence/macro/pull/8581), merge `45dd4e26166f8676f548631f24978580b4d8a723`, and [Terminal #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840), merge `d21fa05ad8d934bb4d70731587ab2df64a28c194`. Installed 12-control proof at 06:41:04Z, SHA-256 `ac1ec230ce6ba56d0f24a05e8fb00bea36f94a5cb3737ec80ea10d58d59cfc32`, retained in #8581. | Injected engineering conformance only; no acquired cohort, new cadence, basis or market pilot. |
| Calendar | [Macro #8602](https://github.com/mastermindx-market-intelligence/macro/pull/8602), squash `0e80cf14572b52c10ea58dda3686bd7d5cb00adc`. Installed 10-control proof at 09:34:38Z: 6,066 bytes, SHA-256 `42cfdc16a4f67b93fee7bc68aa8904fd21040f15cf1936209b601e9cb83b4e4e`. | Exact calendar observation and conformance do not supply the remaining identity, basis, daily or incumbent evidence. |
| Native reference | [Macro #8607](https://github.com/mastermindx-market-intelligence/macro/pull/8607), accepted `6d14f398564dce1d0f68daf956315cf7e9d19520`, squash `7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575`; [required CI 37609426098](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37609426098) PASS. Installed proof process 93607 exit 0 at 11:56:09–15Z; exact linked records below. | Pure installed Native alias reader over actual retained bytes; no Radar candidate admission, historical visibility recertification or transition ingestion. API health proves only its own liveness/version scope. |

The earlier Native draft's **11 unresolved against cap 10** was a real historical blocker. Accepted integration with the separately admitted BATS owner resolved CBOE and produced **718 total / 708 resolved / 10 unresolved**, retaining the unchanged coverage caps. The required gates subsequently passed; #8607 is no longer a blocked draft. This does not repair the eleven old listing-transition rows behind the original prospective attempt: those are a distinct owner/refusal population, and their evidence remains intact. The historical failed gates and diagnostic records below must remain attributable to their original source and inputs.

### Native installed proof: actual custody and preserved refusals

The exact executed [Native remote proof](../../research/live_entry_radar/rs_pullback_launch/verification/installed_native_conformance_remote.py) and [M2 lineage wrapper](../../research/live_entry_radar/rs_pullback_launch/verification/run_installed_native_proof_m2.py) are archived as verification evidence. Their fixed source, target and artifact bindings describe the observed attempt; a future execution requires fresh matching evidence through the existing owner.

The complete records are linked rather than copied into this handoff:

| Record | Exact identity |
|---|---|
| [Installed Native conformance](../../research/live_entry_radar/rs_pullback_launch/INSTALLED_NATIVE_REFERENCE_CONFORMANCE_2026-10-07.json) | 9,168 bytes; SHA-256 `24502c48927c99cdc05c08fdc599a6162351e5fd250bfec64fb7e9cec6d89156` |
| [Positive release lineage](../../research/live_entry_radar/rs_pullback_launch/INSTALLED_NATIVE_REFERENCE_LINEAGE_2026-10-07.json) | 4,689 bytes; SHA-256 `e74975051f764f18b44a8cbbb82a60ef5b693fd8a63c75e514d6bf6770e51b41` |
| [Composite delivery receipt](../../research/live_entry_radar/rs_pullback_launch/INSTALLED_NATIVE_REFERENCE_DELIVERY_2026-10-07.json) | 810 bytes; SHA-256 `9b9f3fc78cbdfed338937c80e818d6a4acf4febf9f98d42d387c215ddcfba6bd` |

At that observation, installed checkout was `f1966d3fdae3f14f42c8e026958f74590d72f9fe`, while the running API process reported release `7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575`. The records preserve this difference. Both checkout and process-build refs have exact positive release-ancestry receipts and the same thirteen protected source/artifact hashes, plus the required DataOS import-tree and API source bindings. Both repositories are shallow; no `is-shallow=false` prerequisite or fabricated installed-local ancestry is claimed. The installed proof records its unavailable local ancestry as null and is accepted together with the positive external lineage record.

The pure installed reader called `VendorAliasTable.from_records`, `resolve` and `vendor_symbol_for` over actual retained installed bytes at **`1791374169888567767` ns** (`2026-10-07T11:56:09.888567767Z`). MU resolved to `SEC:US-XNAS-MU`, reverse lookup returned MU, and SPY/QQQ/SMH remained null/refused. Missing or naive decisions, absent native clocks and tampered seals refused; conservative nanosecond rounding and half-open validity controls passed. These were actual present reads and in-memory controls, not proof that an earlier Radar decision possessed those bytes.

The original owner-input read remains **`1791354276802797000` ns**. Its complete prospective-reference block remains SHA-256 `0e07e498d7a6983c8752a53d719281b07c30d334895c0b418edbbcc160145856`, with MU bound and SPY/QQQ/SMH's original refusals unchanged. Queries around that retained cutoff test reader behavior against evidence read now; they do not backdate the verifier or create a historical Radar receipt.

The actual retained master has 2,383 rows, code version `75a2bfce6dd95ee921d05d719cfc67976de17145`, generated at `2026-10-07T10:11:04`. The sidecar retains 165,493 historical rows and 2,807 current nodes computed at `2026-10-07T10:11:06Z`. CBOE and ETHA are resolved. IBIT has canonical ETF master identity `SEC:US-XNAS-IBIT` while its graph row remains `ENTITY_TYPE_CONFLICT` with null security/issuer. Preserve that consumer refusal. The graph loader and HTTP Native semantic route were not executed; direct artifact checks and local `/api/health` must not be relabeled as those proofs. No provider call, regeneration, deployment or restart occurred within the Native conformance proof.

### v2 reader and producer: source delivery ahead of paired installed proof

[Macro reader #8618](https://github.com/mastermindx-market-intelligence/macro/pull/8618) merged as `67c1d8155d9194825f6cb301967d6b1c1f91b433`. Its 10:34 installed record is a **hash/import proof only**: 1,848 bytes, SHA-256 `09a8ce307d610f65b7e1c79d9c8fb6e40259e1fbcde4a3c3346fac934a4b7909`. Keep the v2 harness installed until the paired proof finishes.

[Terminal #843](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/843) merged at **12:26:21Z** as `e963eefb3ac1984008caae922d6f43bfafa9d827`, from accepted `642fa4cd3d0340ad90952588ac48ca2d4f3e0d8b`. [Required CI 37609414595](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/37609414595) passed all ten jobs; the normal workflow approval returned 201 at 11:48Z. Postmerge verification process **73169** passed, confirming all four accepted source blobs at the squash; the remote branch was already deleted. Its receipt is `/private/tmp/rs-pullback-terminal-v2-postmerge-1791376323200563000.json`, 798 bytes, SHA-256 `b4d755964ff534b823cc7373e083fdd250c16c327759aa5de2e74f94c7c61182`.

**Normal Terminal v2 deployment and paired installed conformance remain pending.** The [preserved original paired proof](../../research/live_entry_radar/rs_pullback_launch/verification/installed_basis_conformance_original_reviewed.py) is 11,304 bytes, SHA-256 `03410cd59d4ece1e8d7caa221cd2c16a2bce273d9ebe68b6753a10cee0ad2e20`; it was never executed on the host. Root and an independent reviewer accepted the minimal shallow-aware preparation below after reading the complete delta and wrapper. All eleven source hashes, the actual committed 19-control harness invocation and all three stdlib HTTP framing cases remain exact, including first-page/observation identity and unchanged chart projection after partial failure.

| Preparation artifact | Exact reviewed identity |
|---|---|
| [Installed paired-v2 proof](../../research/live_entry_radar/rs_pullback_launch/verification/installed_basis_conformance_remote.py) | 13,581 bytes; SHA-256 `b1881376715132785dbbe21e1f0f12bdb4fa3dabe03d88970f0da4fd8c682227` |
| [Paired-v2 M2 lineage wrapper](../../research/live_entry_radar/rs_pullback_launch/verification/run_installed_basis_proof_m2.py) | 25,134 bytes; SHA-256 `786671ef45ef94ab62238fe1409e3e72e1faaf77dc2b612b96a1eb0b5658101b` |

The remote requires exact root-supplied installed heads before and after proof, records actual shallow flags, and leaves host release ancestry **UNAVAILABLE_NOT_CHECKED**. The wrapper independently requires actual positive M2 ancestry for both fixed releases and all eleven source-object bindings at accepted, merged and supplied installed refs before immutable lineage/intent and one SSH. Negative or unavailable ancestry blocks execution; a shallow repository with actual positive ancestry is valid. Raw stdout/stderr and status are retained before semantic acceptance; timeout leaves remote completion unconfirmed. Exact nanoseconds are serialized as decimal strings only at the JSON boundary. Independent cloud controls covered source/head/admission/provider/prefix/clock refusals, strict JSON and both repositories' negative/unavailable ancestry paths, without Git or SSH.

Neither final prepared script has executed on M2 or the host. Actual results must be retained after root execution against the real accepted deployment. This scoped preparation preserves separate source/read clocks, original prefix identity, basis-null refusal, future visibility isolation and short-body framing refusal. All retained Terminal rows remain unavailable for positive basis admission; a visible scalar relabel is not authority.

### Split source merged; installed function proof prepared

[Macro Split #8625](https://github.com/mastermindx-market-intelligence/macro/pull/8625) merged as `f2c33b5e1373a344fde232a6750ef479ccfd6331`, parent `70d2bef9662618d9209aad40b534e2fb8ef10864`, from accepted `d657ab26781e87a19d9c8705d5ac293c816acbb5`. The actual merge tree **`2ce5b02de07fbb1a8ba4c8211b403e7d013fa256`** is the reviewed current-main composition. [Required CI 37610310900](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37610310900) passed, and postmerge source verification process **13259** exited 0. The earlier tree `4221f0f1eafc1805c9e284df6030a15b80f2365b` was an intermediate reviewed composition, not the actual squash tree.

The three earlier implementation findings were repaired and independently accepted: incomplete Content-Length EOF and interrupted HTTP framing remain failed evidence, and numeric JSON identity tokens cannot masquerade as strings. The existing CorpActions opt-in function, generic source kernel and pinned reader retain complete/empty/failed/partial attempts, exact decimal lexemes, correction/omission/reversion history, occurrence identity, create-once/conflict rules and actual custody clocks. This owner stores **observed-body hashes/counts and normalized rows, not entire raw HTTP bodies**. Its basis eligibility remains false.

The remote installed proof and separate M2 wrapper are prepared and independently reviewed, **not executed**:

| Preparation artifact | Exact reviewed identity |
|---|---|
| [Installed Split proof](../../research/live_entry_radar/rs_pullback_launch/verification/installed_split_conformance_remote.py) | 39,404 bytes; SHA-256 `62ab08fb2b08687176a90356352f115915b25987ed2210351ef72f2db8192483` |
| [Split lineage wrapper](../../research/live_entry_radar/rs_pullback_launch/verification/run_installed_split_proof_m2.py) | 24,967 bytes; SHA-256 `12992c28b91d93653228dcb6f11f64cd2d3308bac25d80b1d59a292c057c353d` |

The remote script binds twelve exact source files plus accepted registry projections, compiles the actual installed functions, and confines synthetic writes to a private temporary kernel store. Its namespace-only `close_pass` loader deliberately bypasses the broader initializer: success would prove bounded installed function conformance, not ordinary package/application integration, live HTTP API semantics, provider acquisition, factor applicability or operational cadence. The original 37,926-byte preparation, SHA-256 `742bcffd798f8212a42b300320de12bbff18b103ac9b8657132a28546eab47a6`, remains preserved as `installed_split_conformance_original_prepared.py`; it was not executed. Review corrected its merge-tree label and strengthened exact partial-prefix and A/B/A assertions. The final proof checks exact corrected value/body identity rather than only counts and new IDs.

The wrapper requires actual positive release ancestry and exact protected bytes before its single SSH execution, records immutable lineage and intent first, retains bounded raw stdout/stderr before parsing, and does not retry or infer remote cancellation from a stopped local SSH process. Root owns the later installation, execution, reconciliation and acceptance. No prepared script or wrapper changes the program's admission state.

### Actual deployment obstruction and raw-v3 hold

At the supplied **12:24Z** host census, `/dev/vda1` had **77G used / 0 available**. The existing updater's fetch failed after 11:51Z; checkout remained `f1966d3fdae3f14f42c8e026958f74590d72f9fe`. Root is investigating recovery through the existing owner. This checkpoint records no cleanup, manual retry, installation or recovery success. The condition blocks normal Split installation and Terminal deployment; independent source/research preparation can continue within its existing authority.

The subsequent read-only recovery assessment rejects a build on the small candidates alone. Exact failed-fetch orphan `tmp_pack_Cf6wFt` accounts for **49,176,576 allocated bytes**; `git prune-packed -n` identifies **1,173 loose duplicate objects / 200,450,048 allocated bytes**. Its complete M2 candidate manifest is `/private/tmp/rs-pullback-host-prune-packed-readonly-1791376858020410000.json`, 623,990 bytes, SHA-256 `71f84a1c017c274edf89808a95c1a2696e90bfc90b6f8ebb09cae5822820a4cd`, process 88388 exit 0. Index checksums and pack/index trailer bindings passed; pack-body integrity remains unverified. No candidate was removed.

The unchanged normal Terminal build owner, SHA-256 `31d04362f041258524bbce1551befbae7322d2dd80a2f368cf6ae43c98de669f`, skips dependency reinstall for this exact unchanged package/lock pair and hardlinks existing dependencies/public data on the same filesystem. It still copies **103,071,744 bytes** of target source and creates a new build while live and rollback outputs remain. Source plus the current output footprint is a **222,420,992-byte baseline**, excluding directory metadata, fetch, prebuild and compiler peaks. Exact candidate reclamation totals 249,626,624 bytes, leaving only 27,205,632 above that baseline. Physical `f_bfree` bytes were not allocatable `f_bavail`; a fresh actual recovery measurement remains required. The six inactive rotated plaintext logs have a compression estimate only, and existing delay-compress/rotation policy is not an emergency content-preserving cleanup procedure.

The unchanged Macro updater fetches moving `origin/main` with `--depth 1`; M2's f196-to-f2 object census finds 7,235 new blobs and 746,685,551 logical bytes, but local object storage is not a guaranteed negotiated transfer or peak bound. A bounded read-only index comparison is assessing whether any existing packs are wholly redundant while preserving every object, reference and reflog. This checkpoint claims no pack-body verification, pack removal, GC/repack, log rotation, data deletion or restored delivery capacity.

[Macro raw-v3 #8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623), accepted `6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6`, passed [all binding CI 37610526356](https://github.com/mastermindx-market-intelligence/macro/actions/runs/37610526356) but remains **DRAFT/HOLD** until the paired v2 proof is retained. Do not replace its v2 dependency/harness prematurely.

[Terminal raw-v3 #844](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/844) remains **DRAFT**, now at reviewed and pushed commit `a826c945d666f6f34d2dddcf72222568df4dbff3`, with parents `26c03470ff348071086fe3ab7e6b5a69da826660` and newly merged v2 `e963eefb3ac1984008caae922d6f43bfafa9d827`. Prior hosted run [37606825394](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/37606825394) remains red: its inherited test incorrectly assumed that two different calendars could never share a starting logical index. The complete pre-patch integration tree was exactly the already reviewed hosted merge tree `5b89698916059f09c6860bed7b3d5c0da70c7baa`; the only four merge conflicts were resolved to the independently accepted v3 capture blobs. All other incoming-master entries remain exact.

The one-case repair isolates the existing watchlist fixture, uses 2,000 weekday NVDA observations and 1,400 daily BTC observations, preserves the 2.5-day calendar and greater-than-five-index requirements, and checks actual input/consumer clocks and real manual movement. Its first browser run **71984 failed all three ordinary attempts** because the application defaults to 3D while the proof clock is daily. Those failed reports, three traces and screenshots remain retained. The accepted correction selects D through the existing toolbar before splitting and waits for actual daily consumer windows; it changes no product timeframe defaults or shared helpers.

Corrected actual desktop run **78787 passed on its first attempt** at `2026-10-07T12:35:45Z`: one passed, zero retries/skips/flaky results, with Node 26.5.0. Retained consumer states show zero calendar endpoint disagreement, a 364.374-day move earlier, an 800-index start difference, and 696.668-day disagreement for the incorrect logical-copy control. The six other cases, shared helpers and shared fixtures remain unchanged. Root read the exact final diff and actual state JSON and inspected the resulting existing screenshot before accepting commit/push process **85130**, exit 0. Final tree is `6d4b1a7256d313b06ea0e1d66a0e0480e50e3c76`; test blob `d8af167f1fc72533e42ae512f0be4c5838f4d0f0`, screenshot blob `934e16d1ed7c26ed9679f471ebd6ff3d12ab88ba`. The four capture-semantic blobs are unchanged.

Evidence remains under the owned Terminal worktree's ignored `terminal/playwright-report/pane-sync-20261007/`: `desktop-case-2.json` SHA-256 `ff80e7570d4886a7b9a2cb431bd5a389d66135ab3a0d082f7ea36b256750642e`, `calendar-pane-state-2.json` SHA-256 `8d4380f77eb9d33cff22959b345e12a73f18bb3d60b51ed2b1e71444bd6a6222`, and the complete `first-run/` failures. [Required CI 37622577138](https://github.com/mastermindx-market-intelligence/mastermind-terminal/actions/runs/37622577138) is running; hosted Node 20, other required shards and actual v3 delivery remain unproved. No v3 producer release precedes the compatible installed reader.

### Listing research is ready for a bounded owner contract, not application

The independently reviewed [eleven-case listing report](../../research/live_entry_radar/rs_pullback_launch/LISTING_TRANSITION_RESEARCH_2026-10-07.md) is **21,469 bytes**, SHA-256 `5f5e58ff6548e0471ea302566a17eb9057d58440b3a5ff9da933bef751c5acb5`. Root applied only the two source-fidelity corrections: YYGH's amendment was reported **filed** August 31, and PSKY's completed transfer is in the 8-K **Explanatory Note, PDF page 2**. The report retains primary URLs, class distinctions, contradictory directory observations and unknown publisher/OTC/last-session clocks.

| Research class | Cases | Application boundary |
|---|---|---|
| Same-venue class continuity | DOMO→HUCK Class B; YYGH→YFOR Class A | Proposed first two-case implementation; no rename applied. |
| Listing transfers | KHC; ET common LP units; PSKY→SKYD Class B | Preserve canonical identity across venue/class evidence; no transfer inferred from ticker or CIK alone. |
| Old common conversions | ATAI; QRVO; DBRG; WBS | Distinct from consideration securities; exact exit-owner fields and observation law still required. |
| Suspension with continuing shares | GWH | Exact OTC commencement/final delisting unresolved; do not mark the security extinct. |
| Continuing ADS program | CSAN→CSANY | Preserve ADR/ADS versus underlying ordinary-share identity and the undated issuer-page contradiction. |

No event was applied, no old Native refusal was upgraded, and no later attempt was admitted. Research retrieval intervals and public filing/effective dates are not actual identity-owner `known_at` or Radar availability. The proposed DOMO/HUCK and YYGH/YFOR wave needs reviewed class/listing/observation-time evidence, a current-tip lookup repair preserving inception IDs and legacy fetch/store keys, and real consumer cutoff/reverse/mismatch/correction tests. Merely adding `RenameEvent` rows or a `known_at` field to an ungated legacy namespace is insufficient.

A subsequent Native attempt needs a bounded versioned extension of the **existing receipt owner** with immutable attempt identity, predecessor/input/dependency seals, actual acquisition and owner-read clocks, identical-attempt idempotence, same-attempt conflict refusal and coherent publication/history. Keep the original prospective block, MU binding and SPY/QQQ/SMH refusals exact. No new journal, catalog, selector, data owner or historical identity is created by this report.

### Ordered continuation and parent completion boundary

1. Reconcile the exact safe disk recovery through the existing operational owner, retaining the failed updater observation and actual recovery evidence.
2. Complete normal deployment of the postmerge-verified Terminal #843 source and run the reviewed paired v2 installed proof before replacing the installed v2 harness.
3. Observe normal installation of merged Split and run the reviewed one-attempt installed function proof, retaining lineage, intent, raw output and scoped result through the existing evidence owner.
4. Complete Terminal #844 required CI for the accepted actual-browser repair and reconcile any new current-main delta without altering accepted capture semantics. Deliver raw-v3 Macro reader before Terminal producer, after the v2 dependency is complete.
5. Review and implement the bounded existing identity-owner extension and later Native-attempt history. Separately qualify actual permitted raw/split acquisition, cohort, cadence, finality and capacity through existing owners; no automatic dual fetch or new scheduler is implied.
6. Bind actual PIT daily leader/pullback rows and faithful incumbent `engine/entry_signal.py::assess` inputs/outputs, construct the complete pilot/nonfire/failure/ambiguity population, and rerun Phase 1 before baseline/outcome work.

The original research state model, labels, frozen H1/H2/H3 gates and **total-program DONE_WHEN** remain below. The newest nominal 15-minute interval remains unavailable under the unchanged 900-second finality law; the 4096-attempt cap does not demonstrate 90 prospective sessions. Current daily publication cannot refresh stale constituent rows. Catalyst absence remains unknown without coverage. Global minute-aggregate/research/archive licensing remains closed by the operator-confirmed `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`; do not reopen it without new evidence.

Continue the commissioned work through the next safe existing-owner dependency; this checkpoint does not terminate the parent mission. No detector, score, calibrated probability, UI admission, outcome tuning, C4/F1 firing, new ledger, scheduler, publication owner or rank/gate/size/order authority follows from these component receipts.

## Preserved historical checkpoints and research contract

The following historical body is retained from canonical handoff blob `76d082a02ff72dc37aa29ea7d7866d65dbde9b60`, SHA-256 `453ea340a06149ff75d3b46e52c8331e7f934fec0d6f561e10d4c836f07ade49`. Only stale checkpoint heading labels were changed to identify their historical scope. Pending/current statements below describe their original observations; the cumulative checkpoint above owns the supplied current delivery frontier. Original Phase-1 attribution, negative admission, source receipts, research state model and total-program DONE_WHEN are preserved.

## Prior delivery and next-source checkpoint — 2026-10-07, 09:04Z

Observed at: 2026-10-07T09:04:43.216371Z. Parent `WS:LIVE-ENTRY-RADAR`; **MISSION_COMPLETE: false**.

Phase 1 is complete through its permitted negative result. The overall market panel remains **NOT_ADMITTED**, H1/H2/H3 remain **NOT_TESTED**, and every authority flag remains false. The historical Phase-1 event and research contract remain below. The current source-delivery evidence and next actions are recorded here.

### Delivered retention component

[Macro #8571](https://github.com/mastermindx-market-intelligence/macro/pull/8571) merged the original Phase-1 result as `47a3a248ba9228b498376d2bdc170fd61e38dac0`. `PHASE1_ADMISSION_2026-10-07.json` remains exact at SHA-256 `a4e00a5c191917dc8c64fb74ca3348827ab9bd47d9ad8a03a1130a50fde36e9f`: 29 refusals and no market pilot or outcome claim.

The source-retention slice is delivered in [Macro #8581](https://github.com/mastermindx-market-intelligence/macro/pull/8581), merge `45dd4e26166f8676f548631f24978580b4d8a723`, and [Terminal #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840), merge `d21fa05ad8d934bb4d70731587ab2df64a28c194`. Hosted checks, reviewed source identities, Macro installation and the canonical Terminal build were verified. Terminal deployment finished at 06:38:17Z; at 06:39:02Z the deployment identifier, origin HTML and public HTML all matched the accepted Terminal commit and served HTTP 200.

At 06:41:04Z, the actual installed producer/helper and Macro reader/harness passed all 12 injected conformance assertions through atomic temporary stores. The complete installed receipt is retained in Macro #8581, SHA-256 `ac1ec230ce6ba56d0f24a05e8fb00bea36f94a5cb3737ec80ea10d58d59cfc32`. It establishes installed engineering behavior at that observation time. It enrolled no runtime cohort, fetched no provider bars, and did not admit an adjustment basis or market pilot. The original synthetic conformance artifact remains historical and byte-identical.

### Calendar and identity delivery

[Calendar PR #8602](https://github.com/mastermindx-market-intelligence/macro/pull/8602) is ready for review at `84358749e1fcad33fc2badc96e38225508c4a610`, with hosted delivery CI pending after current-main integration. It binds the exact Terminal session projection through an actual single bounded read and preserves its original clock/capsule for replay. Invalid visible calendar input refuses only the affected candidate. The first hosted run found a real CI selection regression; the correction preserves fresh main's price-panel/PTSE suites and uses a separately curated calendar test job. The local differential gate passed with zero introduced or inherited violations, keeping the 132-job content-probe limit unchanged. Semantic review, CI-scope review and final proof freeze passed. Calendar merge and installed-path proof remain pending at this checkpoint.

[Native identity PR #8607](https://github.com/mastermindx-market-intelligence/macro/pull/8607) remains **DRAFT**, without merge-on-green, at `0c0dc42e0c071b6786741df1d210584e6bd71554`. Source and actual artifact review passed for draft delivery. Only MU received a native binding; SPY/QQQ/SMH remain explicit canonical-owner refusals. The original four native reference observations and actual owner-input clock are retained. A CI fixture that dropped the three new native evidence columns was repaired and independently verified; canonical time guards remain intact.

The native draft has a binding data blocker: current official listing inputs yield **718 total / 707 resolved / 11 unresolved** against the unchanged limit of 10. Both affected data gates remain red. An untouched current-base builder reproduces the count. PSKY is the additional unresolved name; a fresh official-directory diagnostic also found it absent, which is not proof of delisting. Do not raise or skip the cap, replace the gate with baseline equality, restore stale artifact counts, force a binding, or merge this draft because code CI passes. Exact input/artifact hashes and the diagnostic receipt are in the PR. Preserve the separate FISV owner's scope.

The later control-plane CI runs found that the two new exclusive jobs were omitted from the explicit curated-job inventory. Each branch added its own reviewed job name while retaining the exact equality assertion, dependency audits, planner and ceilings. Independent module-AST checks and protected-file freezes passed; both four-test inventory/closure/fallback/packing sets passed. Calendar integrated main `46ec48ecbf0b3dfddd9cb4ba083ee83a00af51bd`, preserving the concurrent `ticker-news-qbus` registration. Native integration also intersects main's separately admitted BATS venue; its source union and unchanged data gates require review before further delivery. The native artifacts have not been regenerated or granted a new result.

### Prior declaration and basis-refusal slice

Operation `rs-pullback-launch-basis-binding-20261007-sol-005` uses protected Mastermind `1fc040f7343dde73fec3556dd3bf9bc8c1b18129`; the prior retention/calendar/reference operations retain their original protected pin `ee120e80f5d5e0344c453dd7cbf4108b9c429b38`.

The current candidate extends the existing Terminal capture envelope and Macro decoder. It preserves sealed v1 prefixes, records v2 response adjustment declarations, and retains declaration changes even when OHLCV values are equal. A complete incompatible response remains evidence while the existing chart stays unchanged. Suppressed captures do not create new minute revisions. Terminal's four-file producer passed 325 affected/D0 tests and independent real-writer review, and is committed as `29224303b192bf70c2692227239a62cde1ee0c6b` in [draft PR #843](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/843). Its hosted checks are running; its producer release remains held for the compatible Macro reader. Macro's source passed 165 tests plus 85 subtests. Independent review reproduced and closed future-version visibility and malformed outer-schema failures; all 19 joint conformance checks reproduce exactly against the committed Terminal source. The accepted new proof SHA-256 is `8fbb51cc41e9acf7bb70be23cd4d86d030dfa15c42b38c2d1e3d9ff7aaa4ed49`. Their isolated branches are both `claude/rs-pullback-basis-v2-20261007`; Macro prepares against the immutable reviewed calendar dependency above.

The Macro candidate removes scalar basis inheritance. Every retained Terminal row carries null basis and a typed `TERMINAL_BASIS_UNPROVEN` refusal; identifiable source rows stay unavailable even if a caller overwrites their scalar label. No basis-file reader, invented owner-attestation schema or positive admission method is introduced. The new `SOURCE_BASIS_DECLARATION_CONFORMANCE_2026-10-07.json` distinguishes immutable raw evidence and source unavailability from separate direct-input synthetic aggregation controls. A response flag, self-sealed metadata, and a separately fetched latest factor table do not establish a shared adjustment vintage.

The compatible reader checks envelope integrity, seals, sequence and capture IDs immediately, while payload-version and ordering semantics apply only after explicit receipt enrollment and visibility. Thus an intact unsupported future record preserves every earlier raw row, revision identity and full frame; it refuses when visible. The CI delivery repair transfers the entire bridge suite to the existing exclusive calendar job, preserves other price-panel/PTSE suites and covers the 12-file literal dependency closure with 17 explicit paths. Independent scope/freeze review passed. Full differential gate process 55503 passed with zero introduced or inherited findings. After current-main integration at `46ec48ecbf0b3dfddd9cb4ba083ee83a00af51bd`, process 55756 again passed with zero introduced or inherited findings in 321.7 seconds; the content probe is 132 jobs / 5,421 seconds / 10 packs within unchanged limits. The six semantic source blobs remain exact. Subsequent calendar dependency integration changed only an AST-identical inventory comment. A dependent reader draft may run hosted checks in parallel, but cannot merge before calendar; installation order remains Macro before Terminal.

### Authorized continuation

Finish the calendar's required hosted checks, merge the reviewed head, and verify the installed reader against the installed projection. Complete current-main integration and hosted delivery checks for the independently accepted declaration slice. Deliver the compatible Macro reader before any Terminal v2 producer deployment, then run paired installed conformance with injected transport and temporary files. Keep the native identity draft blocked until the existing owner resolves its real data gates.

The next source implementation is active as `rs-pullback-launch-split-evidence-20261007-sol-006`, under the same protected `1fc040f7343dde73fec3556dd3bf9bc8c1b18129`. Source inspection at Macro `d69dd101c3cc2d2f430332ad66bad185ed63e4f8` established the concrete owner path: opt-in split-history acquisition alongside CorpActions, a family adapter using the existing `market_memory_source_kernel` object/receipt/generation/HEAD primitives, and one row in the existing dataset registry. The worker has a five-path source/test/document claim and must establish clean custody at fresh main. It has no provider, credential, production-store, schedule, commit or push authorization. The new opt-in route is explicitly `https://api.massive.com/stocks/v1/splits`; the existing close-pass split/dividend endpoints, configuration and consumers remain unchanged. Preserve exact decimal tokens, actual nanosecond clocks, complete-empty and failed attempts, and A/B/A acquisition history. Use the generic kernel; do not copy SPY's daily identity, availability policy or content-only capture identity.

Current Terminal captures request `adjusted=true`. A separately fetched split snapshot cannot prove the factor vintage of those values. Positive basis admission therefore still requires a separately reviewed unadjusted capture path through the existing Terminal owner or actual provider-documented response-atomic vintage evidence. Do not invert old adjusted prices with new factors, introduce another catalog, or accept a caller's self-sealed positive attestation. Split endpoint and convention facts are grounded in [Massive's split API](https://massive.com/docs/rest/stocks/corporate-actions/splits) and [split coverage/migration guidance](https://massive.com/knowledge-base/article/does-massive-support-normal-and-reverse-splits). This bounded slice retains evidence; reconstruction, provider equivalence and live admission remain separate gates.

The split-evidence source candidate completed 489 affected tests, including 71 focused cases, through the real injected transport, generic kernel and pinned reader. Independent review found three concrete defects before acceptance: short Content-Length EOF could be labeled complete; interrupted chunked HTTP could escape without a retained failure; and numeric JSON ticker tokens could compare equal to string identities. The author is repairing these within the original five-path claim. Independent persistence tests passed correction/omission/reversion, concurrent create-once, orphan and uncertain-publication recovery, pinned replay and actual read-clock refusal. No source acceptance or live activation is claimed.

Operation `rs-pullback-launch-unadjusted-capture-20261007-sol-007` is now implementing the next raw-side dependency through the existing Terminal owner. The accepted v3 design adds closed `chart_adjusted` and `research_unadjusted` roles paired with true/false request flags; an explicit `--capture-unadjusted-minutes` mode makes one bounded request chain per named symbol and preserves every existing noncapture chart field. It uses the existing 40-day 1m request profile, with no chart watermark, overlap optimization or automatic dual fetch. Cadence/request costs and live acquisition remain separate decisions. Compaction partitions the existing latest-complete baseline by role/request basis; inherited partial/empty recovery counts remain unchanged. The current author gate passed 405 affected tests, including 159 capture cases; independent review and a compatible Macro v3 reader are still pending. No v3 writer release is allowed before that reader is installed.

Other open admission dependencies remain: the complete pilot/nonfire/failure population, actual first-seen 1m cohort/cadence/history, stable benchmark/sector identity, PIT daily leader/pullback receipts, and the faithful `engine/entry_signal.py::assess` incumbent path used by `scripts/build_stock_library.py`. Catalyst coverage stays unknown where evidence is incomplete. The 900-second finality rule still makes the newest nominal 15-minute window unavailable; the 4096-attempt retention cap is not a 90-session accrual guarantee. Global source licensing is already closed by the operator-confirmed `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md` and must not be reopened without new evidence.

No outcome tuning, detector authority, score, probability, UI admission, new ledger, scheduler, publication owner or decision engine is authorized by these component receipts. Preserve the negative result and continue the next safe existing-owner dependency in the same session.


## Historical cumulative Phase-1 checkpoint — 2026-10-07

Operation: `rs-pullback-launch-phase1-20261007-sol-001`. Parent: `WS:LIVE-ENTRY-RADAR`.
Procedure: Mastermind `9a24ef2c4b27ac95a4d1f72f5eae1073657cd7c2`, skillpack 1.0.1/bootstrap 1.
Macro census `309f88c6c209bdc9fb611de0018fb619d9351b37`; fresh implementation base
`007e0cccbd06f089605ba122efc658f406043dd3`. Relevant Entry Radar/daily/incumbent source
is unchanged across that base movement. Terminal `ad36a332cd4b53af1d917a94f6fb3a10e27dad84`.

**Phase-1 market-data verdict: NOT_ADMITTED. Parent MISSION_COMPLETE: false.**
The new adapter produces input frames only. No detector or label implementation is claimed.
Independent review of source candidate `1c76e954f74a8cf74c3b8e7fce7a0d3b81f49d6a` found
six bounded receipt/causality defects; all were repaired with seven added regression methods.
The exact code-CI step passes 57 tests (30 RS + 27 frozen-panel). The final source head and
hosted checks belong to this branch's pull request; this checkpoint preserves the evidence
frontier without claiming a future merge. The current immutable census includes an explicitly
identified caller-bound qualification-window envelope, preserving original owner-output fields.
The original research and proposed scientific gates below remain preserved; the current
[Phase-1 result](../../research/live_entry_radar/rs_pullback_launch/PHASE1_RESULT_2026-10-07.md)
owns the latest engineering/evidence disposition.

# RS Pullback Launch — Sol Implementation Handoff

**Parent research commission:** RS Pullback Launch / Intraday Low-Detection Intelligence  
**Research status:** COMPLETE  
**Parent program implementation status:** PHASE 1 — DATA NOT_ADMITTED; offline input implementation built, source acceptance pending  
**MISSION_COMPLETE:** false for the total build program  
**Authority:** Chairman has asked Sol to take the completed research forward; this handoff itself grants no production/trading authority.

## Mission

Take the completed RS Pullback Launch research into engineering and empirical validation end to end.

The goal is to determine whether, among already-qualified relative-strength leaders in controlled pullbacks, Mastermind can detect a PIT intraday state in which relative performance / selling-pressure evidence improves before absolute price visibly reverses — and whether that state improves downside control, launch forecasting, or economic timing enough to justify product integration.

Do not assume the edge exists.

## Highest-authority starting points

1. Re-pin current protected `mastermindx-market-intelligence/Mastermind:docs/sol_skills/INDEX.md` and load required same-commit procedures.
2. Read the research package:
   - `research/live_entry_radar/rs_pullback_launch/RS_PULLBACK_LAUNCH_RESEARCH_2026-10-06.md`
3. Treat the research evidence pins inside that document as evidence anchors, not current admission.
4. Re-census current Macro and Terminal heads before any code change.

Persistence base observed when this handoff was saved:
`macro/main@309f88c6c209bdc9fb611de0018fb619d9351b37`.

## Core ruling

Build this as an **extension of existing Entry Radar / canonical entry evidence owners**, not a parallel entry engine.

Reuse:

- `engine/us_leader_pullback.py` for daily leader/pullback context;
- Entry Radar readings/events/detectors/live episode ledger;
- PIT observation construction and null law;
- TrialLedger / experiments registry;
- existing cost / replay infrastructure where semantics match;
- Prophet deterministic availability boundaries;
- Terminal intraday storage/qualification after current re-census.

Do not revive archived `bot/phase2.py` as an active owner.

## Research claims to keep separate

H1: incremental launch information.  
H2: lower remaining downside / better MAE.  
H3: net economic timing improvement.

Passing one does not imply the others.

## Immediate execution target

### PHASE 1 — DATA ADMISSION + PILOT EPISODE PANEL

Do this before UI, scoring or production wiring.

1. Re-census exact intraday data holdings and owner semantics.
2. Freeze a canonical 1m→15m/30m bar law with explicit `known_at`.
3. Establish identity, adjustment basis, session calendar, missing-bar and revision law.
4. Bind PIT daily leader/pullback context and incumbent Entry Engine inputs.
5. Construct a small complete pilot panel containing successes, failures, nonfires, missing inputs and ambiguity cases.
6. Implement PIT mutation tests — changing future bars or later corrections must not alter an earlier detector state.
7. Produce a coverage/refusal census and an admission verdict.
8. Stop before outcome-driven threshold tuning if the data plane is not admitted.

### Phase-1 DONE_WHEN

A fresh session can reproduce the pilot population, feature rows, clocks and labels from immutable inputs and every exclusion/refusal is named; OR the program has a defensible `NOT_ADMITTED` result naming the missing evidence.

## V1 research state model

`ELIGIBLE_LEADER → PULLBACK → EXHAUSTION → ARMED → PIVOT_FORMED → PIVOT_CONFIRMED → LAUNCH`

with transitions to:

`INVALIDATED | DISTRIBUTION | TREND_BREAK | EXPIRED`

Critical meanings:

- `ARMED`: attention / optional research probe only; reversal not confirmed.
- `PIVOT_FORMED`: fully completed 30m pivot exists; high/low are now fixed.
- `PIVOT_CONFIRMED`: a later completed observation crosses fixed pivot high + registered buffer.
- `LAUNCH`: outcome only; never feeds backward into the detector.

An unfinished 30m bar may be described as developing using completed 15m information, but its eventual 30m high/low/close are unavailable.

## Primary proposed labels

Let `E` be the prescribed entry-reference price and `A` the frozen volatility scale.

Primary 120m launch:

- upper barrier = `E + 1.0A`
- lower barrier = `E - 0.5A`
- label = upper reached before lower.

Primary downside:

`MAE_ATR = max(0, E - min(future_low)) / A`

Primary low-in label:

`MAE_ATR <= 0.25`

Low-in and launch stay separate.

## Required controls

- random qualified-leader timestamp;
- any pullback in a qualified leader;
- RSI turn;
- MACD-histogram turn;
- first green 15m;
- first green 30m;
- completed 30m pivot + break;
- common-MA pullback;
- faithful incumbent Entry Engine assessment.

Strong B0 must already include primitive stock, market and sector returns plus leadership, pullback geometry, location, time-of-day, volatility, liquidity, catalyst context and incumbent assessment. RS must earn incremental information over that baseline.

## Frozen proposed acceptance gates

Freeze before outcome access; do not relax after seeing results.

- H1 launch information: ≥2% relative Brier improvement over B0 + positive-effect evidence.
- H2 downside: ≥0.10 ATR mean-MAE improvement at equal coverage + adverse-tail guardrail.
- H3 economics: ≥0.10 common-budget R improvement per eligible episode, positive expectancy under doubled costs + tail guardrail.
- Stability: positive direction in ≥70% quarterly folds with adequate name/period diversity.
- Prospective review: ≥90 sessions with actual availability, latency and cost observations.

## Hard prohibitions

Do not:

- build a second lifecycle, event store, trial ledger, scheduler or notifier;
- grant rank/gate/size/order authority;
- reuse C4 as a firing detector;
- use reserved F1 as a shortcut;
- invent probabilities before calibration;
- create a 0–100 score first;
- require L2/L3 before L1/OHLCV incremental value is proven;
- infer “no news” from missing coverage;
- hindsight-select support/pivots;
- condition the study only on episodes that later confirm.

## Likely paths, subject to current owner recensus

- `engine/entry_radar/`
- `engine/entry_radar/replay/` or an adjacent versioned intraday-outcome namespace
- `research/live_entry_radar/rs_pullback_launch/`
- bounded research scripts under `scripts/`
- discriminating tests under `tests/`
- Terminal intraday qualification paths only if current source law confirms that owner.

## Total-program DONE_WHEN

The mission is complete only when:

1. the data/source law is accepted;
2. historical controls and ablations are complete;
3. claimed effects pass frozen gates;
4. prospective first-seen validation passes;
5. probability output, if any, is calibrated;
6. canonical owner integration is complete without authority widening;
7. all human/machine consumers read the same canonical evidence;
8. paired prospective evidence shows whether this improves the actual incumbent Mastermind decision process;
9. the existing decision/sizing owner separately admits any binding use.

If the edge fails, close the program with a falsification record. Do not force a signal into production.

## First response expected from the Sol implementation session

Recover current source, then immediately advance Phase 1. Return a current owner/collision census, exact research operation boundary, data-availability matrix, and the first concrete implementation/result — not another generic plan.

## Continuation: retained source observations (2026-10-07)

Operation: `rs-pullback-launch-source-retention-20261007-sol-002`.

The preceding Phase-1 checkpoint is historical. Its delivery completed in [Macro PR #8571](https://github.com/mastermindx-market-intelligence/macro/pull/8571), squash `47a3a248ba9228b498376d2bdc170fd61e38dac0`. The concluded hosted gate and merged-file identity were verified. Phase 1 closed through its permitted negative result: **NOT_ADMITTED**, 29 refusals, H1/H2/H3 **NOT_TESTED** and all authority false. Its admission artifact remains byte-identical.

The next source-retention slice uses Terminal's existing producer and per-symbol atomic store. [Terminal PR #840](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/840) adds an explicit bounded 1m capture option, immutable capture-prefix receipts and retained corrections/failures. Existing scheduled defaults remain unchanged. Macro's new `engine/entry_radar/replay/terminal_minute_observations.py` reads actual bytes, creates an actual owner-read receipt and decodes eligible observations for an explicitly supplied decision cutoff. The existing Phase-1 selector remains the revision and aggregation owner.

Recover this slice through:

- [Reader/source contract](../../research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_READER_CONTRACT_2026-10-07.md).
- [Exact local synthetic conformance receipt](../../research/live_entry_radar/rs_pullback_launch/SOURCE_RETENTION_CONFORMANCE_2026-10-07.json).
- Reproducer: `scripts/entry_radar_rs_pullback_source_retention_check.py --terminal-source /absolute/path/to/mastermind-terminal`.
- Focused suite: `tests/test_entry_radar_terminal_minute_observations.py`, added to the existing frozen-panel/RS code-CI step.

The joint proof uses the real producer, atomic temporary file, bounded reader and canonical selector with injected transport and clocks. It checks A/B/A, fractional volume, entire earlier-frame invariance, future malformed semantic isolation, late-first-read conflict and partial-failure refusal. The contemporaneous latest 15m/full frame stays unavailable under the unchanged 900-second finality rule.

Independent review exposed the omitted-cutoff path, enabled empty-file recovery, contradictory pagination identity and automatic HTTP redirects. Their discriminating regressions and final source identities are recorded in the paired delivery evidence. Review, hosted CI, merge, deployed source identity and market admission remain separate gates; this source checkpoint does not claim an unrecorded delivery result.

No provider fetch, runtime cohort enrollment, new schedule, outcome experiment or owner authority is established by the synthetic receipt. Before actual accrual, bind cohort/cadence/finality/capacity through the existing source owner and attach the existing operator-confirmed `research/licenses/MASSIVE_ENTITLEMENT_RECORD.md`, which already closes the global licensing gate for minute aggregates, research and archival retention. The 4096-attempt cap is not a 90-session guarantee. Continue by resolving the next concrete existing-owner admission dependency: stable listing identity and basis, calendar law, actual daily/incumbent receipts, or actual first-seen observation custody. Preserve nonfires, failures and all remaining refusals. The parent program is incomplete.
