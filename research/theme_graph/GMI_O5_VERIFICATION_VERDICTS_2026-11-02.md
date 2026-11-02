# GMI completion commission (2026-10-21): O5 independent verification verdicts — 2026-11-02

**Status of this record.** Verbatim return of ORCH-VERIFY (O5), an Opus 5.5 read-only
orchestrator commissioned by the Fable Meta-CEO seat (session 6f14c2da) after PRs #10482
(relationship integration, main 17040f00) and #10099 (GMI explorer, main fd27c31a) merged.
O5 read origin/main at bca436e58f70 in its own clean worktree, ran
`scripts/gmi_coverage_proof.py` itself (report_version a9f996d7dbf9), and mutated nothing.
The seat judged the packet by artifact on 2026-11-02 (worktree clean at bca436e5, coverage
outputs present, the G-UI-8 concatenation confirmed at `_activity_market_rows`) and ACCEPTED
it as verification evidence. Verdicts are separate per acceptance boundary, as §12 of the
master plan requires: boundary 3 (no promotion) MET; boundaries 1 and 2 NOT MET with every
remainder owner-named. The CI baseline was MEASURED-OPEN at return time (run 41397096175
still in progress); the seat owns that run.

Seat follow-ups taken from this packet: G-UI-8 fixed in the same PR as this record
(row dedup in `_activity_market_rows` plus `duplicate_rows_dropped` and a regression test);
DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT A25 corrected to 69 paths / 11 test files / 12 pytest
steps; the #10099 G-UI-7 wording corrected on the PR body (symbol_directory `security_name`,
else the ticker). G-UI-5 and the resolver name field stay with their owners (commodities copy;
Data OS identity).

---

# ORCH-VERIFY (O5) return: GMI 2026-10-21 completion commission

Verifier: Opus orchestrator seat, MODE READ_ONLY, not an author of the work.
Source: origin/main bca436e58f70 (2026-11-01T23:27:16-07:00), read from the worktree I minted.
Labels: OBSERVED means read from bytes or command output. INFERRED means my reading of that output.

STATUS: PARTIAL. All verdicts are graded. Two items are MEASURED-OPEN because their external runs have not concluded:
- CI run 41397096175 is still running.
- No US engine commit has landed since 10-21, so the legacy theme state has not refreshed.

## RESULT

### Verdicts

1. **Original GMI development (D2E, W3B, W3C): NOT MET.**
   - D2E is still accepted and has not changed.
   - The C01 publication 040b is still immutable.
   - W3B production readers are still unbound, and no successor-generation sealing exists.
   - There is no W3C receipt for the US+CN post-selection cohort.
2. **Descriptive economic intelligence, including the §8.2 envelope: NOT MET.**
   - US activity coverage is 0.0005 and China is 0.0000, against a 95% target.
   - Taxonomy is FAIL: 67 of 68 micros are RESEARCH_UNADMITTED, and no owner-disposition contract exists.
   - The §8.2 release is missing contradiction and stale-evidence cases in both domains.
   - E5 precision is OWED, E4 recall is 0.3487, and not_assessed cells remain.
   - No task-success rate exists.
   - The Terminal #868 hold also keeps this boundary OPEN.
3. **Advanced/predictive, check that no promotion occurred: MET.**
   - No rank, size or gate consumer reads the relationship stores or activity stores as authority.
   - Every authority cap read is false.
   - Zero activity edges have been projected.
   - Scope of the check: engine/, scripts/, app/, lib/ on bca436e5.

### W3 chain on the incumbent producer (receipts only)

| Packet | State | Receipt (OBSERVED) |
|---|---|---|
| T-03: bind trusted owner readers | NOT MET | `data/theme_graph/shadow_theme_state.v1.json` (d056aea2, 2026-11-01, generation b0b84f6a, mode `shadow`): 663/663 subjects carry `IDENTITY_UNAVAILABLE` and `MEMBERSHIP_UNAVAILABLE`, and 18 carry `RIGHTS_NOT_ADMITTED`/`RIGHTS_UNAVAILABLE`. `engine/theme_graph/theme_state_production.py::_validate_qualification` raises `"S1 has no accepted specialist-purpose authority binding"` for any rights `QUALIFIED` leg. The only change since 10-21 was #9639 (1c6814d1, 10-23). It added v1-bundle schema compatibility and refactored a rights import. It made no production binding. |
| T-05: qualify and seal the current generation | NOT MET | Same file: eligibility is `NOT_QUALIFIED` with `[D2E_UNSEALED]` on 663/663. `rg -F neuralweb.theme_state.v2 data/` finds no v2 production generation artifact. `activity_membership_state.v1.json` qualification is `NOT_QUALIFIED [D2E_UNSEALED]`. |
| C-01: W3C post-selection cohort, US+CN | NOT STARTED (blocked on T-05) | No cohort receipt found in history since 10-20. China identity is not qualified for 1019/1019 (coverage proof remainder `cn IDENTITY_NOT_QUALIFIED 1019`). |
| T-06: natural refresh and correction | NOT STARTED (blocked) | No successor generation exists to refresh. Shadow is recomposed nightly (daily.yml:5679 `--mode GRAPH_SHADOW_STATE`), but that is diagnostic only. |
| T-07: sole-state successor migration | NOT STARTED (correctly) | LEGACY `data/neuralweb/theme_state.json` is still the incumbent (`neuralweb.theme_state.v1`, authority display-only). See the LEGACY freshness finding below. |

**LEGACY freshness finding (OBSERVED).**
- `data/neuralweb/theme_state.json` has `generated_at 2026-10-21T08:16:31Z`.
- `theme_phase_history.jsonl` last advanced in ad6e5a82, "engine: regime update 2026-10-21".
- There has been no "engine: regime update" commit on main since 10-21. The engine-render, cortex and asia lanes did commit in that period.
- So LEGACY is preserved, meaning not replaced, but it has not refreshed for 12 days.
- INFERRED cause: #10255 (c2772cc4, 10-31 23:29) carved the oversize qledger out of every wholesale nightly commit. That points to the wholesale engine commit having failed since 10-21. Whether the 11-02 nightly lands an engine commit is MEASURED-OPEN.
- This matters for T-06/T-07: the rollback baseline the successor gates compare against is currently stale.

### G-UI adjudications

**G-UI-7, resolver display-name field: CONFIRMED as a missing owner field. It is not a #10099 defect. The #10099 wording is inaccurate.**
- OBSERVED: neither `data/theme_graph/identity_resolution.parquet` (196,355 rows) nor `data/reference/security_master.parquet` (3,107 rows) has a name column.
- OBSERVED: the docstring of `scripts/gmi_explorer/model.py::_display_name` says: "The identity resolver carries no name field today, so the fallback name source is the dated symbol directory column `security_name`". The code then falls back to `(ticker, "ticker")`.
- The PR body's "resolver name, else filing name" is not what the code does. The code uses symbol_directory.security_name, else the ticker.
- Smallest lawful action: the seat corrects the G-UI-7 log text. Adding a resolver or master name field belongs to the Data OS identity owner and is a separate packet.

**G-UI-8, `--activity-proposals` double-count: REAL, but it does NOT change the coverage verdict.**
- OBSERVED: `read_store()` appends `store_dir/probation/activity_proposals.jsonl` to the queue. `build()` then reads every explicit `--activity-proposals` path again. `_activity_market_rows` (line 809) concatenates the two with no dedup.
- Measured A/B on bca436e5 with identical inputs. A = default ledger only (report a9f996d7dbf9). B = the same plus `--activity-proposals data/theme_graph/probation/activity_proposals.jsonl` (report ed573dcacf42). Results:
  - All 10 gate verdicts and measured values are identical.
  - All remainders are identical, US and CN.
  - All dispositions are identical.
  - Only the counters double: `proposals_seen` a1_schema_rows 2→4, proposed 1→2, ratified_valid 1→2, total_rows 238→240. The `theme:hbm_packaging` per-micro counts go (1,1,0)→(2,2,0).
- INFERRED: the numerator cannot move because `_activity_view` counts issuers with `current >= 1`.
- Smallest fix, as a build packet, not done here: dedup by resolved path in `build()`, or skip an explicit path equal to the store ledger, or dedup by row key in `_activity_market_rows`. Add a test asserting that `proposals_seen` stays the same when the store ledger is passed explicitly.

**G-UI-5, `site/commodities.html:1023`, claimed inherited: CONFIRMED inherited.**
- OBSERVED: the ZH stamp comes from `templates/_commodity_decision_workspace.html.j2:213`.
- `git log -S "不代表已验证的商品直接敞口" origin/main -- templates/_commodity_decision_workspace.html.j2` returns `14799f153a16 2026-10-20 ... (#9878)`.
- Blame on line 213 returns 947550b1 (#10306, 2026-10-31, "fix(copy): drop the unearned word from the commodity name stamp"), a one-line edit of the same line.
- #10099 (fd27c31a, 190 files) touches no path matching `commodit`.
- The negated "已验证" still trips `check_validated_claims`. Fixing it is a copy packet for the commodities owner, not for #10099.

## Boundary detail

### Boundary 1: immutable items and changes since 10-21
- OBSERVED: `git log --since=2026-10-21` on the D2E acceptance doc, `GMI_PROGRAM_RECOVERY_2026-10-16.md`, theme_state_production, owner_readers, w2_qualification, neuralweb theme_state_generation/_reader and company_theme_exposure/ returns only #9639 (1c6814d1, 10-23).
- The recovery doc line 31 still reads "Accepted C01 publication 040b is immutable".
- D2E acceptance (#8540, comment 6103645886, receipt 6120586132) is unchanged.
- #9639 changes, and what they mean:
  - It made `theme_state_production` accept a retained v1 bundle schema sha (`_V1_BUNDLE_SCHEMA_SHA256`), which is a compatibility widening.
  - It moved the owner reader rights import to `adapter.rights`.
  - It added `theme_state_w2_qualification.py` (383 lines).
  - INFERRED: none of this binds production readers or seals a generation. The 11-01 shadow receipt still shows 663/663 NOT_QUALIFIED D2E_UNSEALED.
- OBSERVED: `#6672` (8f1ed858, 10-24, "restart W3A recovery and W3S after rejected seal") is in the stock-identity records lane. It is noted as adjacent and was not adjudicated here.

### Boundary 2: coverage proof (verbatim)
Command (cwd = minted worktree; see DEVIATIONS for why the snapshot path is explicit):
```
python3 scripts/gmi_coverage_proof.py --symbol-directory data/symbol_directory/snapshots/2026-10-31.parquet \
  --research-records research/theme_graph/micro_member_research_addendum_20261016/research_addendum.json \
  --research-records research/theme_graph/microtheme_membership_candidates_2026-10-08.json \
  --out <SP>/cov_default --source-commit bca436e58f7069ff8b52d31074f30726cfecf0e4
```
rc=0. Stdout verbatim:
```
gmi_coverage_proof: wrote 3 files under /private/tmp/claude-501/-Volumes-Mastermind-claude-ssh-worktrees-macro-main-4a794e55c3bdbd60-program-handoff-orchestration-3fcb8d/6f14c2da-02a9-467e-9f37-7c2ebaccfe09/scratchpad/cov_default (report_version a9f996d7dbf9)
```

COVERAGE_REPORT.md core denominators and gates (verbatim; report_version a9f996d7dbf9c5cd1196cd604807e5beff207d0549ef0eddc3852dddb1b48d7c, manifest_version e6d4658ffbad222fcd8771930ac3bce5da45922bbd3b835c486601ad876df8b8):

## Core denominators (US and CN are separate; never summed)

| market | securities | issuers resolved | issuers resolved (eligible) | eligible securities | unresolved-issuer securities |
| --- | --- | --- | --- | --- | --- |
| us | 1941 | 1929 | 1927 | 1936 | 4 |
| cn | 1019 | 0 | 0 | 1019 | 1019 |

## Gates

| Dimension | Threshold (verbatim) | Measured | Verdict |
| --- | --- | --- | --- |
| Denominator honesty | 100% of the frozen universe has explicit coverage/status for each promised dimension; issuer/security/activity counts and exclusions are published separately. No arbitrary all-graph denominator. | {"core_markets": {"cn": {"eligibility_counts_sum": 1019, "eligible_securities": 1019, "exclusions_listed": 0, "identity_status_counts_sum": 1019, "issuer_and_security_counts_separate": true, "issuers_resolved_distinct_eligible": 0, "securities_total": 1019}, "us": {"eligibility_counts_sum": 1941, "eligible_securities": 1936, "exclusions_listed": 5, "identity_status_counts_sum": 1936, "issuer_and_security_counts_separate": true, "issuers_resolved_distinct_eligible": 1927, "securities_total": 1941}}, "issuer_security_counts_separate_keys": true} | PASS |
| Principal activity coverage | At least 95% of eligible core U.S./China issuers have a current source-backed principal activity and qualified identity; every remainder has a specific reason and source/owner next step. Assess each market separately. | {"denominator_lower_bound": 1928, "denominator_upper_bound": 1931, "market": "us", "numerator_issuers": 1, "ratio_lower_bound_denominator": "0.0005", "ratio_upper_bound_denominator": "0.0005"} | FAIL |
| Principal activity coverage | At least 95% of eligible core U.S./China issuers have a current source-backed principal activity and qualified identity; every remainder has a specific reason and source/owner next step. Assess each market separately. | {"denominator_lower_bound": 1, "denominator_upper_bound": 1019, "market": "cn", "numerator_issuers": 0, "ratio_lower_bound_denominator": "0.0000", "ratio_upper_bound_denominator": "0.0000"} | FAIL |
| Taxonomy coverage | All 68 currently adopted micros have versioned scope and an owner-reviewed coverage disposition. No forced constituent minimum or parent inheritance to inflate a sparse theme. | {"declared_micro_count": 68, "discrepancy": null, "expansion_micro_count": 303, "micros_without_scope_version": 0, "observed_micro_count": 68, "owner_review_gap": "NO_OWNER_DISPOSITION_CONTRACT", "owner_reviewed": false, "tier_cutoff": "2026-10-21"} | FAIL |
| Correctness | Zero hard identity merges, fabricated named anonymous customers, unauthorized source promotion, future leakage, failed-fetch removals, or magnitude/species conflations in release controls. | null | NOT_IN_THIS_LANE |
| Automatic admission | No automatic positive admission until a per-relation/per-source evaluation supports a one-sided 95% lower confidence bound of at least 95% precision. 59 independent all-correct cases reach approximately 0.9505; correlated disclosures require an adjusted design, not this shortcut. | null | NOT_IN_THIS_LANE |
| Freshness | At least 95% of accessible material filing/corporate-action changes are observed and routed within 48 hours; visible stale/unavailable status is mandatory when source cadence or rights prevent refresh. Validity and retrieval freshness remain separate. | null | NOT_IN_THIS_LANE |
| Corrections | Material confirmed errors are withheld or corrected by the next ordinary publication; the original view remains reproducible and correction latency is measured. | null | NOT_IN_THIS_LANE |
| Product usefulness | At least 90% success on predefined investor explanation tasks, measured separately for EN/ZH and supported desktop/mobile views; exact ID/status/date parity on every release journey. | null | NOT_IN_THIS_LANE |
| Predictive claims | No prediction/allocation promotion from descriptive acceptance. The existing evaluator must separately judge PIT baselines, leakage, costs, robustness, calibration and the specific intended use. | null | NOT_IN_THIS_LANE |

Remainders (verbatim, lines 55-73):

## Remainders (every one has a named owner; no OTHER)

| market | reason | count | owner | next step |
| --- | --- | --- | --- | --- |
| ca | NOT_IN_MASTER | 167 | Data OS security master | decide master admission for the listing |
| cn | CN_LISTED_COUNTS_NOT_AVAILABLE | 1019 | Data OS | install a market-wide listed-count owner for mainland China |
| cn | IDENTITY_NOT_QUALIFIED | 1019 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| cn | NO_ISSUER_EVIDENCE | 1019 | Data OS security master (scripts/build_security_master.py) | china_hk issuer admission via CNInfo evidence |
| intl | UNSUPPORTED_MARKET | 233 | Data OS universe owner | no installed universe owner for this market |
| us | DEFERRED_IDENTITY_EXCEPTION | 1 | Data OS identity-exception owner | resolve the recorded identity exception |
| us | EXCLUDED_ENTITY_TYPE_CONFLICT | 1 | Data OS security master | kept outside the company denominator; own count preserved |
| us | EXCLUDED_ETF_KIND | 3 | Data OS security master | kept outside the company denominator; own count preserved |
| us | EXCLUDED_SUPERSEDED_DUPLICATE_MINT | 1 | Data OS security master | kept outside the company denominator; own count preserved |
| us | IDENTITY_NOT_QUALIFIED | 726 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| us | NOT_IN_GRAPH | 724 | GMI graph population / engine.theme_graph.identity_resolution owner | decide node admission from the master; never inferred |
| us | NO_ACTIVITY_EVIDENCE | 4 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |
| us | NO_ISSUER_EVIDENCE | 3 | Data OS security master (scripts/build_security_master.py) | attach issuer evidence (SEC CIK) for the security |
| us | VENDOR_MEMBERSHIP_ONLY | 1200 | engine.company_intelligence.issuer_disclosure_owner + named GMI curator | native fact -> build_activity_membership_evidence -> make_activity_membership_proposal -> named curator ratification |


Taxonomy dispositions (coverage_report.json): 67 RESEARCH_UNADMITTED, 1 NATIVE_POPULATED (`theme:hbm_packaging`, admitted 1, proposed 1). Expansion tier: US 0, CN 0.

Comparison with the accepted 10-19 manifest (`research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json` at 0221d6e1, OBSERVED):
- Then: US 0/[1926,1931], CN 0/[1,1019].
- Now: US 1/[1928,1931], CN 0/[1,1019].
- So the only movement since 10-19 is one US issuer.

### Boundary 2: §8.2 envelope (committed `research/theme_graph/gmi_relationships_20261021/m2_integration/envelope_print.txt`, last commit 17040f0050d3 #10482; as_of 2026-10-21; panel_sha256 108866ec…a3ca)

Each row has three parts:
- **Committed value (OBSERVED):** what envelope_print.txt says.
- **Contract reading:** INFERRED against the DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT, where E1–E8 are measurement only and the 0.80 targets bind promotion only.
- **Release-bar reading:** INFERRED against the §8.2 release text.

| Cell | Committed value (OBSERVED) | Contract reading | Release-bar reading |
|---|---|---|---|
| E1 assessment | D1: 146 total, 114 assessed, 31 no_supported_result, 1 not_assessed. D2: 137 total, 72 / 64 / 1. | measured | NOT MET. §8.2 requires no not-assessed cells; 1 remains in each domain. |
| E2 role cells | not_assessed=1 in every role cell, both domains. D2 contract_manufacturing and distribution have no known_fresh results (136 searched, no supported result; 1 not assessed). | measured | NOT MET (same reason) |
| E3 parse/judging | Judging ledger PRESENT. D2 parse_outcomes ABSENT. OTHER ABSENT. | measured | partial |
| E4 recall | Overall 0.3487 (83/238; Wilson 95% [0.291, 0.4113]; jackknife 95% [0.2429, 0.4545]; 31 issuers). D1 0.4423 (69/156, [0.3667, 0.5207]). D2 0.1707 (14/82, [0.1045, 0.2664]). | measured; below 0.80, which binds promotion only | MEASURED, below target. Report `m2_recall/recall_report_v1.json`, sha256 915de348…37a8, shasum re-verified equal. |
| E5 precision | Printed: OWED ("no precision sample directory given (--precision-dir)"). | OWED | NOT MET. The only figure is the glm-5.3 blind re-read: 49/100, weighted 0.498 [0.390, 0.607], 0/25 decoys. That is not owner evidence. precision_report.json was never committed. O1 (owner review by a fresh non-authoring reviewer) is still owed. |
| E6 latency | ALL n=1589: p50 5707.39 h, p90 6178.63 h. D1 p50 5722.39 h. D2 p50 5697.3 h. Clock violations 0. package_lag NOT_MEASURABLE. | measured | measured. package_lag remains open. |
| E7 answerability | Answerability measured; "rating OWED" (line 292). | OWED | NOT MET |
| E8 example coverage | Both domains have: outgoing_query, incoming_query, quantitative_fact, unknown_magnitude, anonymous_counterparty, correction, valid_multi_hop, invalid_multi_hop. ABSENT: **contradiction** (D1 and D2, 0 candidates), **stale_evidence** (D1 and D2), and D2 next_publication_reassertion (D1 has it). | measured | NOT MET. §8.2 explicitly names contradiction and stale evidence. |

### Boundary 2: hard errors, admission LCB, freshness and task success
- **Hard errors, automatic admission (one-sided 95% LCB ≥ 95%), freshness (48h routing) and corrections:** the proof marks these measured `null` with verdict `NOT_IN_THIS_LANE` (verbatim above).
  - OBSERVED: no committed artifact on bca436e5 measures them. INFERRED: they are UNMEASURED, so they cannot be MET.
  - Admission: no automatic positive admission is running. The activity ledger holds `ratified_valid 1` by named-curator path, and E5 is OWED. INFERRED: the LCB gate has not been exercised, so it is neither met nor violated.
- **EN/ZH × desktop/mobile task success ≥ 90%: NOT MET (unmeasured).**
  - OBSERVED: `mockups/evidence/gmi-explorer-s1-s5/manifest.json` (schema `mastermind.p0_evidence.v2`, `scripts/capture_page_evidence.py`, generated 2026-10-22) has these properties:
    - 6 pages: /gmi.html, /gmi-index.html, /gmi-issuer-mu.html, /gmi-relationships.html, /gmi-coverage.html, /gmi-states.html.
    - 144 of 144 states captured, 146 files.
    - Access is anonymous only; timing_basis is `lab`.
  - It contains no task-success measurement. The #10099 PR body gives capture evidence, not a success rate.
  - `DEC-GMI-DESCRIPTIVE-PRODUCT-ACCEPTANCE-2026-10-19` line 104 keeps product usefulness ≥ 90% OPEN behind the Terminal #868 integration safety hold (Sol/Chairman, EFFECT_NONE retained).

### Boundary 3: no promotion (scope engine/ scripts/ app/ lib/ at bca436e5)
Commands, run in the minted worktree:
```
rg -l --type py -e 'company_intelligence/relationships|company_intelligence\.relationships|activity_membership_state|activity_history_events|probation/activity_proposals' engine scripts app lib | grep -v -e '/tests/' -e 'test_'
rg -n --type py -e '(rank|size|sizing|gate|gating)\w*\s*=.*(relationship_edges|activity_membership|activity_history|observation_package)' engine scripts app lib   -> no matches (rc 0 via head)
rg -n 'date_provenance' engine/theme_graph/security_navigation.py
```
OBSERVED:
- **Store importers (24 files):**
  - the relationships package itself (10 modules);
  - `engine/theme_graph/{activity_history_bridge,probation}.py`;
  - the producer, proof and display scripts: `bridge_activity_history`, `build_relationship_observations`, `build_thematic_state`, `build_theme_graph`, `gmi_explorer/model`, `propose_activity_membership`, `relationship_m2_{envelope,harvest,judge,precision,recall}`, `relationship_m3_describe`.
  - No `app/` or `lib/` file imports them. None is a rank, size or gate consumer.
- **Authority caps, all false:**
  - `data/company_intelligence/relationships/relationship_edges.json` lines 5/7/8 (gate/rank/size false).
  - `observation_package.v2.json` lines 277/279/280.
  - `data/theme_graph/activity_membership_state.v1.json`: `may_gate/may_materialize_edges/may_publish/may_qualify/may_rank/may_size` all false. Qualification is `NOT_QUALIFIED [D2E_UNSEALED]`, event_count 0, projected_edges 0.
  - `shadow_theme_state.v1.json` authority is all false, with `is_context_only true`.
  - `engine/theme_graph/theme_state_production.py` FLAGS are all False.
  - `lib/economic_propagation.py:14`: "rank, no grade, and no authority".
  - `app/company_supplier_research.py:19`: `_AUTHORITY = dict.fromkeys(('rank','gate','size','trade','prediction'), False)`.
- **Graph:** `data/theme_graph/edges.parquet` has 26,037 edges and **0** with `date_provenance == activity_history`. `security_navigation.py:270,350` admits only `{"seed_constant","curated_changelog"}`.
- **Predictive:** the coverage proof does not measure the Predictive gate (`NOT_IN_THIS_LANE`). The MET verdict therefore rests on the greps above, not on the proof.

INFERRED latent path (not a promotion; flagged for a census):
- `scripts/build_theme_graph.py:262-326` folds `data/theme_graph/probation/activity_history_events.jsonl` into `materialize.build(activity_events=...)`. That writes MEMBER_OF edges with `activity_history` provenance into edges.parquet.
- It applies no qualification gate of its own. The `may_materialize_edges=false` cap lives only in the activity_membership_state artifact.
- The ledger is absent today, so the effect is nil. 29 non-test edges.parquet readers exist. 17 of them use rank/size/gate words and most do not reference `date_provenance`.
- Once a curator-ratified event lands, those readers would see activity edges. Whether any of them is an authority consumer rather than display ordering is UNVERIFIED. Mechanical follow-up for a `scout` census: for each of the 29 readers, does it rank, size or gate, and does it filter `date_provenance`?

### CI baseline
- Run **41397096175** (ci.yml, workflow_dispatch, head 75d7799015e1, covers #10482). Read at 06:59Z and again at 07:04:47Z (300s spacing kept): `status in_progress, conclusion null, run_attempt 1, created 05:58:36Z, updated 06:08:44Z`. That is about 66 min in progress, against a typical 30–34 min. **MEASURED-OPEN.**
- Prior main proofs, all concluded success: 41389256942 at 987b8132 (04:34Z; predates #10482, since 17040f00 is not an ancestor of 987b8132), 41383366922 at e4009c94, 41363446158 at 2f6d6734, 41357580547 at afec10a0.
- **No ci.yml run exists yet on fd27c31a (#10099) or any descendant.** Ancestry is 17040f00 → 75d77990 → fd27c31a → bca436e5 (`git merge-base --is-ancestor`, OBSERVED).
- I did not read jobs, did not dispatch and did not cancel anything.

## EVIDENCE
- Minted worktree, created via the SSD helper: `/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/gmi-orch-verify-124b98d9a1c8ec83`. HEAD = origin/main = bca436e58f7069ff8b52d31074f30726cfecf0e4. Made full via `python3 scripts/worktree_sparse.py full`; status clean.
- Coverage proof outputs:
  - default run: `<SP>/cov_default/{COVERAGE_REPORT.md,UNIVERSE_MANIFEST.json,coverage_report.json}`, report a9f996d7dbf9;
  - stdout: `<SP>/cov_default_stdout.txt`;
  - A/B explicit-ledger run: `<SP>/cov_explicit/`, report ed573dcacf42.
  - `<SP>` = `/private/tmp/claude-501/-Volumes-Mastermind-claude-ssh-worktrees-macro-main-4a794e55c3bdbd60-program-handoff-orchestration-3fcb8d/6f14c2da-02a9-467e-9f37-7c2ebaccfe09/scratchpad`.
- Receipts read:
  - `data/theme_graph/shadow_theme_state.v1.json` (generation b0b84f6af35328ed5510aa620adb36fd, 2026-11-01T10:40:47Z, d056aea26f31);
  - `data/theme_graph/activity_membership_state.v1.json` (2026-11-01T10:40:50Z);
  - `data/neuralweb/theme_state.json` (generated 2026-10-21T08:16:31Z, last commit ad6e5a824334);
  - `data/theme_graph/edges.parquet`;
  - `research/theme_graph/GMI_PROGRAM_RECOVERY_2026-10-16.md:31`;
  - envelope_print.txt and recall_report_v1.json (shasum verified);
  - `mockups/evidence/gmi-explorer-s1-s5/manifest.json`.
- History:
  - `git log -S "不代表已验证的商品直接敞口"` → 14799f153a16 (#9878);
  - blame of `templates/_commodity_decision_workspace.html.j2:213` → 947550b1 (#10306);
  - `git show --stat fd27c31a | grep -c commodit` → 0;
  - `git log --since=2026-10-21` over the D2E/W3B sources → only 1c6814d1622c (#9639);
  - last "engine: regime update" commit is ad6e5a82 (10-21); c2772cc44ef5 (#10255) is the qledger carve-out.
- Code read:
  - `scripts/gmi_coverage_proof.py` (`read_store` ~343, `build` ~1518, `_activity_market_rows` 809, `_taxonomy` hard-coded `owner_reviewed False`);
  - `scripts/gmi_explorer/model.py::_display_name`;
  - `engine/theme_graph/theme_state_production.py::_validate_qualification`;
  - `engine/theme_graph/security_navigation.py:270,350`;
  - `scripts/build_theme_graph.py:262-326`;
  - `.github/ci/legacy-jobs.yml` job `company-intelligence-relationships`: 69 paths, 11 test files, 12 pytest steps.
- CI: `gh api repos/mastermindx-market-intelligence/macro/actions/runs/41397096175` (two reads, at least 300s apart) and one `actions/workflows/ci.yml/runs?branch=main&per_page=5`.

## GAPS
1. CI baseline 41397096175 is not concluded (MEASURED-OPEN), and there is no run on fd27c31a or a descendant. The seat's planned dispatch is still owed. Preflight: do not dispatch over the in-flight 41397096175, because the cancel-in-progress group would kill it.
2. Hard errors, admission LCB, freshness and corrections are unmeasured. No lane on main produces them.
3. EN/ZH desktop/mobile task success is unmeasured, and the #868 hold keeps usefulness OPEN.
4. E5 owner precision (O1) is owed. E7 rating is owed. E8 contradiction and stale_evidence are absent. not_assessed cells remain in E1/E2.
5. Activity coverage: US 1/1928–1931, CN 0/1019. CN identity owner is absent (IDENTITY_NOT_QUALIFIED / NO_ISSUER_EVIDENCE / CN_LISTED_COUNTS_NOT_AVAILABLE, each 1019).
6. Taxonomy: `_taxonomy` hard-codes `owner_reviewed False` and `NO_OWNER_DISPOSITION_CONTRACT`. There is no contract through which the 68 owner dispositions could be recorded. That is missing implementation, not a wait.
7. LEGACY theme_state has not refreshed since 2026-10-21. The cause (oversize qledger blocking the wholesale engine commit, #10255) is INFERRED. Whether the next nightly lands is MEASURED-OPEN.
8. The edges.parquet activity-provenance latent path is not censused (Boundary 3 note).

### Smallest next lawful action per NOT MET
- **B1 (W3B, T-03/T-05):**
  - Bind trusted owner readers so the shadow stops reporting IDENTITY/MEMBERSHIP_UNAVAILABLE.
  - Give S1 an accepted specialist-purpose rights binding, which is a ruling for the rights owner.
  - Then seal a v2 generation.
  - C-01, T-06 and T-07 stay blocked until then.
  - Nearest unblocked step: confirm the 11-02 nightly lands an `engine: regime update` commit, so LEGACY is a live rollback baseline. That needs a receipt check, not a fix.
- **B2:**
  - (a) A build packet for an owner-disposition contract in `_taxonomy`, so 68 dispositions can be recorded.
  - (b) Native activity facts through the named-curator path for US, and a CN identity owner (Data OS).
  - (c) A fresh non-authoring owner review of the 100-item E5 sample (O1).
  - (d) Add contradiction and stale-evidence exemplars to the M2 panel.
  - (e) A predefined EN/ZH desktop/mobile task-success study once the #868 hold releases.
- **G-UI-8:** a builder packet to dedup the ledger, plus a regression test.
- **G-UI-7:** correct the log or PR wording now. Defer the resolver name field to the Data OS identity owner.
- **G-UI-5:** a copy fix in `templates/_commodity_decision_workspace.html.j2:213` for the commodities owner.

### Record corrections for the seat
- DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT A25 says "63 paths … 11 suites". Current `legacy-jobs.yml` reads 69 paths / 11 test files / 12 pytest steps.
- The G-UI-7 log or #10099 body says "resolver name, else filing name". The code does symbol_directory `security_name`, else the ticker.

## DEVIATIONS
- **No fabric lanes.** No verified original root or immediate parent was available to me, and the 10-21 handoff records Fabric `canonical_source_unreadable`. Per the commission, I did the bounded reads myself. No native children and no Workflow were used.
- **Symbol snapshot passed explicitly.** `--symbol-directory data/symbol_directory/snapshots/2026-10-31.parquet` was used because the default `latest.parquet` does not exist on main. `--research-records` was set to the same two files the accepted 10-19 manifest lists.
- **Parquet reads.** The repository's own parquet files were read with plain `python3`, because `python3 -I` lacks pyarrow. No downloaded data was executed.
- **T-packet definitions** (T-03, T-05, C-01, T-06, T-07) come from the commission text plus the 10-21 handoff line 67. No packet table was found in the Downloads plan files.
- **Importer scope.** An earlier pass named only `build_thematic_state.py` as an outside importer. The re-run grep above lists all 24 producer, proof and display importers. The conclusion is unchanged: none is an authority consumer.
- **CI jobs endpoint not read,** to stay within the one-read-per-300s budget.
