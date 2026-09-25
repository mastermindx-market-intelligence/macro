---
workstream: "WS:GMI-THEME-GRAPH"
session: claude/ssd-gmi-robotics-impl-17c9f82c-d191559b616f5c67
model: fable
ended_because: ci_handoff
mission: >
  Implementation carrier and cumulative working checkpoint for
  gmi-robotics-fable-ceo-e2e-20260923-chairman-001: deliver the first production-proven
  granular Robotics theme-intelligence vertical (Precision Motion + Perception) inside the
  existing Theme Tracker / basket/robotics_automation.html workflow by CONSUMING the shared
  GMI foundation built on #7870 (assertion contract, K1 subtype, admission/rights, generic
  paid research API, generic theme-research client/mounts, R4 private binding) and building
  only the Robotics-specific composition, evidence qualification, facets, non-regression
  and real-path acceptance. One Fable principal orchestrates; bounded fabric children build.
state_before: >
  Research/spec/plan/handoff truth existed only on draft/HOLD PR #7773 at
  325be052aa5892f21a399ec0eebc1bd5c65b995a (amended 2026-09-24 for the Semiconductor
  shared foundation). No implementation carrier, no Robotics PICKUP_ACK/START, no product
  code. Macro main at pickup was 3c93f8194f6c2cb19dad21c1347d8b3b8474aa31.
changed:
  - path: "agentos/handoffs/GMI-THEME-GRAPH-2026-09-24-robotics-implementation.md"
    what: "The implementation-operation working checkpoint: receiver identity, packet and procedure pins, the Robotics custody rulings RR1-RR9, the architecture rulings 1-6, the DO_NOT_REDO map, the lane/gate table and the exact next action. Carries RULING 5 (the duplicate Robotics mount partial and its tests are RETIRED -- Robotics mounts by REGISTERING in the shared shell, so neither path survives on this carrier) and RULING 6 (that registration lands AFTER this carrier merges, because the shared registry imports a vertical's composer eagerly at registry-import time)."
  - path: "tests/robotics_research_helpers.py"
    what: "R1 shared test helpers for the Robotics evidence corpus: bundle loading, stamp recomputation and the case-id vocabulary every later Robotics battery reuses instead of restating."
  - path: "tests/fixtures/robotics_theme_research/ (21 synthetic curation_assertion.v1 case bundles)"
    what: "R1 evidence corpus: 21 hand-built curation_assertion.v1 bundles covering the Precision Motion and Perception slices plus the adversarial cases -- syndication, source-authority injection, integrated-assembly double count, retained backdate, review expiry, rights partiality and unresolved identity. Synthetic throughout; no vendor body text is redistributed."
  - path: "tests/test_robotics_research_inputs.py"
    what: "R1 input contract over the corpus: every fixture decodes under the SHARED theme_graph.curation_assertion.v1 reader and all 66 stamps recompute independently, so this vertical cannot quietly fork the shared assertion contract."
  - path: "contracts/market_ontology/robotics_theme_research.v1.schema.json"
    what: "R2 closed served contract for the Robotics research envelope -- deliberately the same 14-key shape as the semiconductor composer so ONE generic paid route and ONE generic client serve both. Pins section_status to ready|degraded|unavailable|refused, and records that top-level limitations carry 'rights_partial' and NEVER name the withheld family (RBV-27)."
  - path: "engine/market_ontology/robotics_theme_research.py"
    what: "R2 the Robotics composer: two slices (precision_motion, perception), five views, evidence selection and the coverage ladder. B2 fix at 23055bc5f89 -- emptiness now outranks omission, so a zero-selection read serves 'unavailable' instead of the PARTIAL state 'degraded'; and 'rights_partial' now requires a selection to be partial ABOUT, because the shipped client renders limitation slugs verbatim and the old token was therefore a member-facing claim of cut entitlements on a paid surface. Both lines were authored by this operation's own R2 commit 37fd0bd35471."
  - path: "tests/test_market_ontology_robotics_theme_research.py"
    what: "R2 composer battery including the RBV-27 leg, extended at the B2 fix with a zero-selection positive control proving the suppression fires on an EMPTY read and not only on a partial one."
  - path: "tests/test_robotics_research_composition.py"
    what: "R2 composition battery: view construction, ordering, and envelope identity against the shared 14-key contract."
  - path: "tests/test_robotics_research_temporal.py"
    what: "R2 temporal battery: as-of correctness, backdate refusal and supersession, so a later-retained correction can never be served as the current statement."
  - path: "engine/market_ontology/robotics_owner_bundle.py"
    what: "R4-reg the private owner-bundle loader. Coverage absence is a typed omission, never a 503. The B2 fix rewrote the served-value block to state what the code actually serves and withdrew a misattribution, and the RBV-27 paragraph now records that neither omission token changes the served payload in any way."
  - path: "tests/test_robotics_owner_bundle.py"
    what: "R4-reg loader battery. After B2 the zero-selection test asserts 'unavailable' with ['slice_scope_unowned'], and the RBV-27 test asserts WHOLE-PAYLOAD byte identity against a bundle composed with omissions=() -- so an empty read cannot disclose even THAT something is withheld."
  - path: "tests/fixtures/robotics_non_regression/ (frozen baseline + README)"
    what: "The recorded pre-change state of every frozen decision surface, so the non-regression battery compares against captured bytes rather than against its own expectations."
  - path: "tests/test_robotics_theme_non_regression.py"
    what: "The non-regression guard over the 32 preserved RBV cases and the frozen decision surfaces: Robotics basket membership and weights, ThemeState, Theme Tracker recommendation/lane/stage, Prophet and member ranking, entry gates, sizing, alerts and trading. Research coverage carries zero automatic decision authority; this battery is what makes that checkable rather than asserted."
  - path: "research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md"
    what: "R7 per-publisher source-rights qualification matrix (the twelve M2 columns) covering every host in the corpus: the terms actually inspected, the proposed v1 representation, a minimum positive witness resolving to a real fixture assertion, and the refusal behaviour while a row is pending. Source counts and public accessibility are not an approval basis."
verified:
  - claim: "Protected procedure re-pinned from one commit and its delta since the packet pin was read."
    command: "git fetch origin master; git rev-parse origin/master; git diff c917a75b0168a524a51b2ba0603a99118e93ef1f origin/master -- docs/sol_skills docs/AGENT_DIALOGUE_SESSION_CLOSE_LAW.md docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md"
    result: "Mastermind master 294b4c00ed668b497edb834be8108f14bc1bee8a; delta = ACTIVE_EXECUTION.md 'Start and recover without administrative ceremony' section (+92) plus INDEX/BOOTSTRAP/COLD_START pointers; Skillpack 1.0.1/bootstrap 1 unchanged."
  - claim: "PICKUP_ACK is durably recorded on the packet carrier with the actual receiver identity."
    command: "gh pr comment 7773 --body-file ack.md"
    result: "https://github.com/mastermindx-market-intelligence/macro/pull/7773#issuecomment-5810063026 (Claude Fable 5.1, Claude Desktop Code session 17c9f82c-8981-43d5-bf95-307691cb27cd, claude8, Mac Studio m2)."
  - claim: "No competing STARTed Robotics implementation child or EFFECT_UNKNOWN Robotics writer exists."
    command: "gh pr view 7773 --json comments | grep -iE 'PICKUP_ACK|START'; gh pr list --state open --search robotics; git ls-remote origin 'refs/heads/*robotics*'"
    result: "Only Sol's 'has not been handed off/STARTed' notices on #7773 before this ACK; no open Robotics implementation PR; no robotics implementation branch on origin. Sol's dependency-coordination comment #7870 issuecomment-5808813275 accepted the shared foundation for Robotics consumption without START."
  - claim: "Shared foundation on #7870 reconciled at its current head; the shared assertion contract is unchanged since the packet amendment and no #7870 hunk touches the two frozen paths."
    command: "gh pr view 7870 --json headRefOid; git rev-parse <head>:<path> for the contract, module, evidence schema, store.py, basket_detail.html.j2, state_of_themes.html.j2; git diff --stat merge-base..head"
    result: "#7870 head c6c67c878b86ebb02782e1dfd394809d8f724426 (Draft/HOLD). curation_assertion.v1.schema.json ff3928f0c54aa164ef8283d9da45af67e6a0d971 (unchanged), engine/theme_graph/curation_assertion.py 9458ec4820095be3df8874f44c784f3ee98bb64c (T04 reference_for_assertion added), evidence.v1.schema.json 8f909df8ee4c5858512035d2dfef21eac982a34d (unchanged). store.py 63b58860 and basket_detail.html.j2 a3d8846b and state_of_themes.html.j2 05017554 are byte-identical to main (frozen hunks not applied). Integrated on #7870: T01 fixtures, T02 contract, T03 rights/admission, T04 K1 subtype (vocabulary.v1.json theme_graph.curation_assertion owner_store, reader engine.theme_graph.curation_assertion.decode_assertion), T05a/T05b earnings, T06 guidance history, T07/T08 semiconductor composer (contracts/market_ontology/semiconductor_theme_research.v1.schema.json, engine/market_ontology/semiconductor_theme_research.py). NOT on the carrier: T09 generic API (lane in flight, closed slice_key enum hbm_packaging|sic_gan_specialty), T10 client (fix lane returned, review pending), T10b include seam (lane in flight), T11 private adapter."
  - claim: "The three external rulings Robotics depends on are read at their exact comment ids."
    command: "gh api issues/comments/5808854275 5808986207; gh pr view 7462 --json comments"
    result: "R4 SOL-R4-PRIVATE-BINDING-20260924-HEALTHCARE-R11 (#7780): Research Vault private store via engine.research_vault.r2_store, key theme_graph_private/v1/assertions/<curation_revision>.json, no public-body shortcut, store-owner nonce proof, positive-only entitlement grace <= 86,400 s, source rights independent veto, shared POST /api/themes/v1/research/{query,evidence}; implementation NOT_GRANTED, live admission held. #7669 ruling 5808986207: ONE guarded include templates/_basket_intelligence_mounts.html.j2 authored by #7870; other verticals ship separately owned partials whose aggregator entry is serialized through that shell writer. #7462: head 31706d7322af55696dc7b2e746ec511b08bd51d7 unchanged; #7870's one-line EVIDENCE_COLUMNS custody question (2026-09-24T03:53Z) unanswered; store column still frozen."
  - claim: "One fresh implementation carrier exists from then-current main on the SSD worktree policy."
    command: "python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create; git checkout -B claude/ssd-gmi-robotics-impl-17c9f82c-d191559b616f5c67 3c93f8194f6c2cb19dad21c1347d8b3b8474aa31; git sparse-checkout disable"
    result: "Worktree /Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/gmi-robotics-impl-17c9f82c-d191559b616f5c67; base = main 3c93f8194f6c2cb19dad21c1347d8b3b8474aa31; #7773 is not the base."
  - claim: "R1 (Robotics evidence fixture corpus + helpers + input contract) is accepted and integrated on this carrier with Robotics-owned paths only."
    command: "git cherry-pick -x d704663282f4 f3a7ebf1c15b; git diff --name-only 4db666779007 HEAD | grep -v '^tests/'; throwaway merge 7f51a2244d15 + #7870 dd5076fae5f4 -> 03f7fab92e51; TZ=UTC python3 -B -m pytest -p no:cacheprovider -o addopts='' -q tests/test_robotics_research_inputs.py tests/test_theme_graph_curation_assertion.py tests/test_semiconductor_research_inputs.py; python3 -B scripts/check_theme_graph_contracts.py"
    result: "Carrier commits b54e593b3da4 (R1, lane rs_20260924T083347Z_39343 on mb, glm-5.3) + 7f51a2244d15 (seat fix after the first READ_ONLY review REJECT: B1 HDS published totals mislabelled as one product group, B2 non-strict JSON NaN/Infinity); 23 files, 100% under tests/. Re-verification READ_ONLY Opus review: ACCEPT_WITH_NITS, 0 blockers, 13 mutations (11 caught); 66/66 stamps recompute independently. Seat gate on the throwaway merge: 60 passed; contracts check exit 0. Recorded nits (not blocking, owed to the next fixture-touching lane): injection fixture publisher should equal its subject label 'Example Reducer Vendor'; HDS residual prose unpinned by the totals loop; component-value-under-all-groups label unguarded outside hds_operating_snapshot; corpus test shells out to git (non-git exports fail)."
  - claim: "R4a (Robotics basket-intelligence mount partial, identity-gated on the exact anchor, plus hermetic tests) is accepted and integrated; the carrier stays collectable and green on main alone."
    command: "git cherry-pick -x 0fb06b8f13dc; seat fix f5f8e8362c5b; TZ=UTC python3 -B -m pytest -o addopts='' -q tests/test_robotics_research_mount.py (carrier alone) and the same plus tests/test_basket_intelligence_mounts.py tests/test_robotics_research_inputs.py on the throwaway merge f5f8e836 + #7870 0c7f637cc63c (90d26c315070)"
    result: "Lane mb rs_20260924T101159Z_59812 (glm-5.3) → carrier 31919764cf9a (2 files, +420) + f5f8e8362c5b (guarded sibling import, strict xfail for the shared seam, URL allowlist, raw-slug pin). READ_ONLY Opus review ACCEPT_WITH_NITS, 0 blockers, 13 mutations (11 caught; the 2 gaps are the nits now taken); attribute-level shape diff vs the semiconductor partial = identity values + data-schema-id + data-slice-labels only; identity gate silent for 15 negative anchors. Carrier alone: 10 passed, 3 xfailed (strict). Merge: 39 passed, 1 xfailed (the documented shared-defect pin). validated-claims checker: offender list byte-identical with and without the partial (65 UNEARNED findings in 12 unrelated templates; the earlier '43' was a truncated line count). Recorded, not taken: the shared-defect pin uses pytest.xfail() at runtime rather than the marker form (flips loudly either way); data-slice-labels carries EN+ZH in one attribute (mandated by the packet, not visible text)."
  - claim: "R2 (Robotics theme-research composer + closed contract + tests over the SAME 14-key envelope as the shared composition contract) is accepted and integrated; the carrier stays green on main alone."
    command: "git cherry-pick -x 5b9513882ba2; seat guards 95d7e6ef41d7 + f257fc8e6a05; carrier alone: TZ=UTC python3 -B -m pytest -o addopts='' -q tests/test_robotics_research_*.py tests/test_market_ontology_robotics_theme_research.py; throwaway merge f257fc8e + #7870 3e3a7956d014 (6ca102dfe221): same suites + semiconductor composition/inputs + curation_assertion; scripts/check_theme_graph_contracts.py"
    result: "Lane mb rs_20260924T102921Z_16517 (glm-5.3) → carrier 37fd0bd35471 (5 files, +3122, all owned). READ_ONLY Opus review ACCEPT_WITH_NITS, 0 blockers: envelope parity PASS (14 top-level keys byte-identical and same order as semiconductor_theme_research.v1; identical required list; 300 composed responses × Draft2020-12 → 0 errors; authority/leak walk 0 hits; shuffle invariance 1200 comparisons byte-identical; shared ResearchQuery/OwnerBundle/ResearchRefusal and 8 private helpers are the shared owner's objects); 7 mutations, all effective ones caught. Carrier alone: 19 passed, 77 strict xfails (the composer needs engine.theme_graph.curation_assertion, so its suites strict-xfail until #7870 lands; the R1 semiconductor-corpus pin was a latent RR9 red since R1 and is now the same strict xfail). Merge: 173 passed, 1 xfailed; contracts exit 0. 14 nits recorded; N1 (ownership side read from does_not_establish / counterparty verbs can invert the Zebra/Skild side — both shipped fixtures land correctly today), N2/N4/N5/N6/N7/N9/N11/N12/N13 are commissioned to lane R2b together with the canonical-id migration; N3 (rights_partial fixture has empty omissions — the caller must populate them, R5/T11 path), N8 (no evidence schema file — parity with the shared owner, question for #7870), N10 (independent_source_count fixed at 1, RBV-26 v1) recorded."
unverified:
  - claim: "T09/T10/T10b/T11 will land on #7870 with the three bounded extensions Robotics requested (theme-dispatch registry, config-driven mount slices, multi-anchor Theme Tracker)."
    what_would_verify: "Accepted #7870 commits exposing a per-anchor composer registry consumed by app/theme_research.py, a partial that reads slices from context/config, and a Theme Tracker mount/client that renders one research entry per anchor; or an explicit shared-owner ruling assigning those hunks to Robotics."
  - claim: "The Robotics composer and fixtures will pass independent review and the seat integration gate on main + #7870."
    what_would_verify: "Second-environment pytest over the Robotics suites on a throwaway merge of this carrier and the #7870 head; independent READ_ONLY review ACCEPT/ACCEPT_WITH_NITS; RBV-01..27 mapped tests green."
  - claim: "Any Robotics live path exists."
    what_would_verify: "R4 nonce proof by the store owner, Orbbec/Twinny + Parker assertions admitted through the shared admission path into the private key space, entitled API returning them, anonymous negative, deployed browser proof."
unresolved:
  - "FABRIC (credential ceremony, Chairman-level, non-blocking): lane host mini2 holds no GLM/MiniMax/Bailian key (~/.glm/config.json is distributed to m1 and mb only per the kit's GLM_ENABLEMENT.md; keys never leave the seat), so every `pool remote mini2 glm` lane ends rc=75 GLM_DISABLED although `pool hosts glm` lists it ELIGIBLE. Robotics lanes are restricted to m1/mb (4 slots shared with the Semiconductor/Finance/other seats' queues); the mission is not frozen, only slowed."
  - "RULED (Sol #7780 5813801605, option A, disposition blob ec80dd1468082b81fa9dd56852aede3ce041e6b9): hooks 1-4 (closed route dispatch by trusted registration; configuration-driven mount; multi-anchor Theme Tracker entry; exact schema/version binding, no regex) are the #7870 owner's additive work; Robotics supplied its closed registration values, cohort declaration and rights-family request 7 at #7870 5813896754 and acknowledged at #7780 5813897159. Binding for Robotics: emission fails closed on unmapped source families (every Robotics host is unmapped today → served path NOT_BUILT until the rights owner registers rows; no Robotics allowlist); every response carries `slice_scope_unowned` and evidence follows the same cohort filter (R2b addendum S2); `system_replay` without a supported as-known identity mapping is refused (R2b addendum S1, code `identity_as_known_unsupported`); the accepted identity-gated partial is the lawful interim for hook 2."
  - "RULED (Sol #7780 5814333887, 12:42Z, rights admission): JPX/TDnet, HKEX and issuer/vendor families are NOT approved by analogy to sec_edgar; Robotics owns ONE bounded qualification unit over its retained source register — a compact source/representation matrix (publisher, source class, representation, terms actually inspected, restrictions, existing owner decision, minimum witness, exact refusal behaviour) plus a narrowly scoped proposed registry/prefix change with rights_class unresolved, returned for explicit adjudication BEFORE any emission; pending = refused incl. dependent prose/evidence; example.invalid fixture-only. Lane R7 (packet R7_rights_matrix; read-only terms inspection, no source re-acquisition, no registry edit) dispatched 12:45Z; its output file is research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md. Sol also registered an hourly native PARENT_ORCHESTRATOR watch on #7886 (attention routing only; no runtime START inferred)."
  - "SHARED (canonical theme ids, #7870 5812295091): assertions must carry `theme:<slug>` from engine.theme_graph.identity.theme_node_id while the mount/API anchor stays the crosswalk slug. The accepted R1 corpus is slug-keyed on all 71 assertions (same defect the owner acknowledged on its own fixtures) and the running R2 lane started on the pre-ruling packet; lane R2b (packet R2b_canonical) re-grounds the fixtures, makes the composer match through the identity owner, counts slug-keyed assertions as `scope_slug_keyed:<n>`, and takes R1 review nits n1-n3."
  - "SHARED (flip day): the Robotics include line in `_basket_intelligence_mounts.html.j2` must land only AFTER the semiconductor partial's identity gate (owner's stated fix) — with the grammar-only gate both partials would mount on the Robotics page and the single-mount client would bind the semiconductor section (reviewer mutation L). Request 6 to the shell writer carries that sequencing condition."
  - "SHARED (T09): request model slice_key is closed to semiconductor slices; Robotics slices precision_motion|perception need anchor-theme dispatch to a registered vertical composer. Request posted on #7870; no /api/themes/v1/robotics fork."
  - "SHARED (T10/T10b): generic partial hardcodes data-slices; Theme Tracker mount is single-anchor (ai_semiconductors). Robotics needs config-driven slices per anchor and a per-anchor Theme Tracker summary. Request posted on #7870."
  - "SHARED (#7462): curation_assertion column not persistable; Robotics store round-trip tests xfail(strict=True) pinned; no Robotics store patch."
  - "SHARED (R4/T11): live admission NOT_GRANTED; Robotics real evidence bodies stay outside the public repo; fixture-only until the nonce proof and adapter qualification clear."
  - "Executive OS MCP unauthenticated in this non-interactive seat; lifecycle edges live on #7773 (ACK/START) and this carrier; fabric dispatch uses the installed pool CLI on remote lane hosts (seat m2 is load-gated)."
next_actions:
  - "On R2b return: bundle pull-back (base 8e478b2feed0), throwaway-merge gate, READ_ONLY Opus review, cherry-pick; on R3 return the same with review_brief_R3. Then R4b/R5/R6 as their gates clear."
  - "(superseded) R2 composer, R3 non-regression and R4a partial are queued on m1/mb (worktrees rob-r2 at f3a7ebf1c15b = pin + R1, rob-r4a at the pin, rob-r3 full data on m1; mb rob-r2 at ad3d15b0e36f); on each return: bundle pull-back, seat gate on the throwaway merge, READ_ONLY Opus review, cherry-pick onto this carrier, checkpoint."
  - "R4b (facets / Theme Tracker entry) after Sol's build-out ruling on #7780 5811066300 and T10c/T10d; R5 after the R4 nonce proof + T11; R6 after deploy."
  - "Dispatch lane R1 (Robotics evidence fixtures as valid theme_graph.curation_assertion.v1 payloads, hostile variants) and R3 (legacy decision non-regression + public-leak freeze) to remote lane hosts at #7870 head; seat gate + independent READ_ONLY review; cherry-pick Robotics-owned files onto this carrier."
  - "After R1 acceptance: lane R2 (Robotics F04 composer, same envelope as the shared composition contract, slices precision_motion|perception). Then Robotics partial/facet UI once T10/T10b are accepted; then real-path qualification once R4 live admission clears."
do_not_redo:
  - "Task 1 shared assertion contract (consume #7870 ff3928f0/9458ec48); Task 2 store column (#7462); Task 3 K1 subtype (T04 on #7870); the generic API route (T09); the generic client/mount (T10/T10b); the private publication mechanism (R4/T11); the 46-source research sweep; the approved spec/plan."
  - "Do not turn #7773 into the implementation branch; do not edit #7870/#7462/#7669 paths from this carrier; do not create a Robotics store, bucket, table, publisher, scheduler, watcher, identity or product master."
danger_areas:
  - "Full-fidelity real Robotics assertion bodies must never enter this public carrier, evidence.parquet, site/ or public R2; fixtures use the frozen reference shape with example.invalid or already-public vendor pages only."
  - "A fixture-green composer, a 200 from the shared API, or a rendered shell is not the vertical; completion is the real-path law in the master packet section 3."
---

# GMI Robotics — implementation operation working checkpoint

OPERATION: `gmi-robotics-fable-ceo-e2e-20260923-chairman-001` (child of `gmi-robotics-bom-research-20260923-sol-001`; parent `WS:GMI-THEME-GRAPH`).
RECEIVER: Claude Fable 5.1 (`claude-fable-5-1`), Claude Desktop Code session `17c9f82c-8981-43d5-bf95-307691cb27cd`, account claude8, Mac Studio (m2) seat. PICKUP_ACK: #7773 issuecomment-5810063026.
PACKET: `agentos/handoffs/GMI-ROBOTICS-MASTER-FABLE-CEO-HANDOFF-2026-09-23.md` at #7773 `325be052aa5892f21a399ec0eebc1bd5c65b995a`; spec blob `d248fd1b4c9b48df8f5c95c3bdd742c2a8ef7007`; plan blob `d0a04e96c874395ae51cf44281039c99527dcd86`; research foundation blob `9d8f7df56f56cfc82a4152b3ef1db81f19219aae`; acceptance cases blob `2d83b015afdaa0c8f870e39f1aefd45786ef5d27`.
PROCEDURE PIN: Mastermind `294b4c00ed668b497edb834be8108f14bc1bee8a` (Skillpack 1.0.1/bootstrap 1).
CARRIER BASE: Macro `main` `3c93f8194f6c2cb19dad21c1347d8b3b8474aa31`; branch `claude/ssd-gmi-robotics-impl-17c9f82c-d191559b616f5c67`.
SHARED FOUNDATION PIN: #7870 `c6c67c878b86ebb02782e1dfd394809d8f724426`.

START: #7773 issuecomment-5810224304 (2026-09-24T08:02Z). STATE AT THIS COMMIT: `STARTED / WAVE_2_R2B_R2C_R3_R7_INTEGRATED`; `ROBOTICS_FIRST_VERTICAL: NOT_BUILT`; `MISSION_COMPLETE: false`; `EFFECT_UNKNOWN: none`.
SHARED FOUNDATION REFRESH (08:30Z): #7870 head `70fde3c79956bba5b9c4e2365a97b4e4b3b1c3ef` — T10 generic client (`site/assets/js/theme-research.js`, css, Theme Tracker mount in `state_of_themes.html.j2`, `tests/test_semiconductor_theme_research_ui.py`) integrated with CI wiring; T09/T10b/T11 still in flight. Contract/module/evidence blobs unchanged from `c6c67c87`.
SHARED FOUNDATION REFRESH (09:40Z): #7870 head `0c7f637cc63c` (dd5076fae5f4 → 0c7f637cc63c is company-intelligence T05a/intake only; `engine/theme_graph`, `app/theme_research.py`, the research templates/client/css, `contracts/`, the semiconductor composer and `scripts/build_theme_detail.py` are byte-identical to `8e478b2feed0`, the lane pin). Semiconductor checkpoint 5811603234: T07c (= Robotics request 5, public helper exports) queued on m1; T09fix/T11a/T10d on mb; T10c on m1; no build-out ruling yet on #7780.
R1 ACCEPTED + INTEGRATED (09:35Z), R4a ACCEPTED + INTEGRATED (11:00Z) and R2 ACCEPTED + INTEGRATED (11:37Z): see `verified`. #7870 head at this commit `3e3a7956d014`: T09 transport landed (`app/theme_research.py`, `slice_key` closed to the two semiconductor slices, handler hard-wired to the semiconductor composer, no registry) — Robotics request 1 (anchor-keyed dispatch) stays open under Sol's build-out ruling; the owner has queued T10e (canonical scope match) and T10f (partial self-gating), the same fixes Robotics carries as R2b and R4a. Consumed since: shared-owner canonical-id/mount/anchor answers #7870 5812295091 (10:22Z) and the #7669 compatibility acceptance of the single guarded include 5812507700 (10:38Z). Carrier head after this commit carries b54e593b3da4 + 7f51a2244d15 + this record.
SEAT EXECUTION (13:20Z→): with both keyed hosts (m1, mb) held at active=2 by other seats' live lanes for hours and mini2 keyless, Sol's continuation ruling (#7780 5814541566 §1: direct bounded seat completion of a finite critical fix with no STARTed executor, independent review preserved) was applied to R2b, R7 and R3; all three dispatchers withdrawn, remote worktrees removed, capacity evidence recorded. Every seat commit was reviewed by an independent Opus READ_ONLY `general-purpose` agent (builder ≠ reviewer) on the merge tree AND the carrier alone. Carrier chain since the last checkpoint: 5d95a26e9220 (R2b) → 55e6fe150bec (R2b-fix) → 30bfe8d75979 (R3) → e57230d3da58 (R2b-fix2 + R2c) → 62bce5afef2a (R7 doc) → b56ba8121ef1 (R3-fix) → 3356bf2abb5 (R2b-fix3) → 760cb4ccc8f (R3 nits) → 54454e2c3a7 (R2b-fix4) → abbf5f4e509 (R2b-fix5) → 109d0990ccc (R2b-fix6) → 29330ead303 (R2b-fix7) → 2b309d2c442 (R2b-fix8) → 2eba8891072 (R2b-fix9) → 5de66e2872c (R2b-fix10) → 7d938c2411c (R2b-fix11) → 3d73de31e21 (fix11 nit). Composer review history — TWELVE independent Opus READ_ONLY rounds on the ownership side, eleven of them REJECT. Rounds 1-3 rejected prose readings (`no_selected_assertions` on non-empty selections; counterparty verbs flipping the side; patient slots; comma-set `by`; appositive/relative clauses naming the subject). Round 4 = FIRST architecture ruling (47 inversions: the open agent/patient resolver RETIRED for a closed template grammar). Rounds 5-7 rejected boundaries, the agency lexicon, then 39 inversions across six agency families. Round 7 = SECOND architecture ruling: agency in free prose is an OPEN set, so the four subject-naming templates and the whole agency/dirty-tail apparatus were RETIRED and the side came from the CURATED `object.source_product_label` parenthetical. Rounds 8-9 then inverted the curated inputs themselves; round 9 = THIRD ruling (every curated input becomes a closed grammar). Round 10 rejected two content grammars, one a regression I introduced (`_PRODUCT_FOR` tracked CAPITALISATION, not agency: `for A Client` served where pinned-neutral `for a client` refused); fix10 refused the closed GRAMMATICAL class instead. Round 11 then falsified fix10's premise verbatim and corrected a measurement I had PUBLISHED as fact (my ‘zero unclassified looseners’ claim was false — hand-picked party space; the reviewer's exhaustive sweep found 26,410, incl. a silently dropped `behalf`). The three findings that ended it: agency needs NO connective at all (transitive participle `to Skild AI Representing Fanuc`, English genitive `to Fanuc's Nominee Skild AI`), so a closed grammatical class has nothing to refuse; a SHAPE rule degenerates in TITLE case into the same word list that already lost; and even a tighter shape leaves a residual. [fix11 = FOURTH and FINAL architecture ruling: the ownership-side parse is RETIRED ENTIRELY. Every ANNOUNCED_ARRANGEMENT serves `announced_party`; 206 lines deleted; neither the curated label nor the `establishes` prose is read, so no input of any shape can produce a side. RBV-10 is preserved — its text is silent on WHICH party and its core is the untouched REPORTED_FACT branch; the directional side appears NOWHERE in the master packet, the implementation plan or the acceptance doc, so it was an implementation invention discharging R2 nit N1, not a requirement. The curated direction is still served VERBATIM in four fields (`object_product_label`, `establishes`, `does_not_establish`, `next_evidence`): a reader still sees who sold what to whom; only the ENGINE's inferred claim stopped. Cost = 10 cohort rows lose a CORRECT `announced_seller` (2 assertions × 5 views), traded for zero wrong sides, and they serve nothing today since none of the eleven Robotics publishers has a row in config/theme_sources.yml. DEFINITION_VERSION HELD at 2026-09-24.1 (shared envelope, const-pinned in both vertical schemas, feeds the `generation` fingerprint); the named price is that `generation` does not hash the body, so a cached generation now maps to a changed `companies` body — tolerable at zero consumers, and the joint bump is an OBLIGATION carried with the v1.1 `object.subject_role` enum at #7870 5825733887 item 7] → ROUND 12 ACCEPT, ZERO BLOCKERS, six nits (nit 1 `import re` dead → fixed in 3d73de31e21; nits 2-5 were five wrong counts of MINE, corrected in that commit message; nit 6 accepted as-is by ruling). The reviewer proved it two ways: a TOTAL static proof (fix11 `_ownership_role` reads only `predicate`, `statement_mode` and `temporal.business_valid_from`, uses zero module globals, has four reachable returns, and the strings `announced_seller`/`announced_acquirer` do not occur in the function — covering the infinite input space, not a sample) and a 536,448-case dynamic differential through the real entry point with 27,132 directional sides as positive control at the parent: fix11 produced ZERO. Cohort diff reproduced exactly (305 rows, key set identical, exactly 10 change, only `companies` differs across 100 composed responses); 5 of 6 new/changed tests fail against the parent; a reintroduced one-line direction fails 5 tests (teeth proven); all 28 inversion triples verified truthful to their round labels, with exactly the 14 `r11-*` entries still inverting at fix10; all 19 deleted names at zero references; no missed pin or consumer (the frontend reads `role` only as an ARIA attribute and `compose_robotics_research` has no non-test caller). Sol rights return: #7780 issuecomment-5815643294.
SHARED-OWNER OBSERVATIONS found while integrating (posted on #7870 after the composer verdict): `app/theme_research.py::_filter_bundle_for_rights` passes UNMAPPED `source_uri` through (contradicts option-A fail-closed) and copies `interpretation_blocks` unfiltered; `SOURCE_PREFIX_FAMILY` has no `https://` prefix; `_EvidenceBody.assertion_ref` grammar refuses the `theme:` segment; stale "canonical theme id" wording in `_theme_research_mount.html.j2`; a slug-keyed literal in the shared assertion test. Registered divergence: the shared composer at 3e3a7956d014 passes the `system_replay`-without-vintage case through; Robotics refuses it with `identity_vintage_unsupported`.
REQUESTS POSTED ON #7870 (shared owner; no reply yet at this commit): issuecomment-5810227724 (1 T09 anchor-theme dispatch registry; 2 config-driven mount slices; 3 per-anchor Theme Tracker entry) and issuecomment-5810595339 (4 client envelope identity per mount — `TR_SCHEMA`/`TR_SLICE_KEYS` are hard-pinned to semiconductor; 5 public export of time-mode/generation helpers).

## Fable custody rulings inside the approved architecture (RR = Robotics ruling)

- **RR1 — one shared assertion contract, consumed at a pinned head.** `theme_graph.curation_assertion.v1` is #7870's. Robotics imports `engine.theme_graph.curation_assertion` lazily; tests that need it are `xfail(strict=True)` on a base where it is absent and pinned to #7870 head `c6c67c87`. `published_at_grain_mismatch` accepted; `source_ref_for` consumed unchanged; `industrial_context` not emitted by Robotics v1. No copy, no variant, no divergent enum. Any Robotics need beyond v1 goes to the shared owner as a bounded additive request (the SOL-HC-R12 v1.1 path), never a fork.
- **RR2 — store column is #7462's.** Robotics opens no `engine/theme_graph/store.py` patch. Persistence round-trip tests are strict-xfail until the shared column lands.
- **RR3 — K1 subtype is DO_NOT_REDO.** T04's `theme_graph.curation_assertion` owner store (vocabulary.v1.json) and `reference_for_assertion` are consumed. Robotics adds Robotics-specific K1 hostile cases only if a discriminating red is found in the shared binding.
- **RR4 — Robotics composition is Robotics-owned and path-disjoint.** `contracts/market_ontology/robotics_theme_research.v1.schema.json`, `engine/market_ontology/robotics_theme_research.py`, `tests/test_market_ontology_robotics_theme_research.py`, `tests/fixtures/robotics_theme_research/`. It emits the SAME envelope as the shared composition contract (`schema, definition_version, generation, request, native_subjects, summary, companies, industrial_views, economics, expectations, evidence_refs, authorized_coverage, limitations, authority`) and consumes the shared `ResearchQuery`/`OwnerBundle`/`ResearchRefusal` types so the generic client and route can serve it. Slices are `precision_motion` and `perception`. Views map: composition = BOM/documented inclusion/capability rows (configuration-scoped quantities); commercial = arrangements, deployment targets, reported deployments, ownership events; capacity = reported operating measures (orders/backlog/sales as flows/stocks, never lead time); economics = reported financial measures with denominator/basis or explicit not-disclosed; manufacturing = process/material rows (unavailable-with-reason in v1 unless evidenced). No score/rank/alpha/signal keys; authority all false.
- **RR5 — transport is the ONE shared route.** No `/api/themes/v1/robotics`. Robotics requested on #7870 that T09 dispatch on `anchor_theme_id` to a registered vertical composer with vertical-owned slice validation. Until accepted, the Robotics composer is exercised only in-process.
- **RR6 — UI consumes the generic client and the #7669-ruled seam.** `basket_detail.html.j2` and `state_of_themes.html.j2` stay frozen to #7870's accepted hunks. Robotics ships at most one separately owned partial whose aggregator entry is serialized through the shell writer, and requested config-driven slices per anchor plus a per-anchor Theme Tracker research entry on the generic client. No Robotics-only JS/CSS framework; no owner intelligence in browser JS.
- **RR7 — private publication = R4.** Robotics is a registered dependent of `SOL-R4-PRIVATE-BINDING-20260924-HEALTHCARE-R11`. Real Robotics bodies (Orbbec/Twinny, Parker, Schaeffler/Hexagon, Zebra/Skild, PTC/TPG, Sanhua, HDS) are curated as payloads outside the public repo and admitted only through the shared adapter after the nonce proof; fixtures on this carrier use the frozen reference shape.
- **RR8 — non-regression is Robotics-owned and starts now.** `tests/test_robotics_theme_non_regression.py` freezes `robotics_automation` basket members/weights, Theme Tracker lane/stage/recommendation, entry fields and member ordering from committed inputs, plus public-leak guards over `site/state_of_themes.html`, `site/basket/robotics_automation.html`, `site/**/*.json` and the tracked evidence parquet.
- **RR10 — fixtures are contract doubles, never the live product.** Public fixtures model the approved real cases (Orbbec/Twinny, Parker, Schaeffler/Hexagon, Zebra/Skild, PTC/TPG, Sanhua, HDS, Stabilus/Synapticon) with `synthetic: true`, reviewer `fixture`, placeholder `research-vault://fixture/<slug>` retention refs, null digests and public URLs already cited in the public research foundation; facts are public, the product (reviewed, clocked, retained, maintained assertions and their composition) is not. Live bodies are curated separately under RR7 and differ in bytes, so `curation_revision` never collides with a public fixture (RBV-28 no public twin).
- **RR9 — development base vs carrier.** Lane worktrees are minted at the #7870 head so workers can import the shared foundation; the carrier receives only Robotics-owned files on top of main. The seat proves every integration on a throwaway merge of this carrier with the #7870 head before cherry-picking, and CI on this carrier must stay green on main alone (lazy imports + strict xfail).

## Lane plan

| Lane | Scope | Depends on | Host/model | State |
|---|---|---|---|---|
| R1 | Robotics evidence fixtures: 21 cases as valid `theme_graph.curation_assertion.v1` payloads + helpers + input-contract tests (packet R1_fixtures) | RR1, RR10 | mb glm-5.3 lane rs_20260924T083347Z_39343 | ACCEPTED (review REJECT → seat fix → ACCEPT_WITH_NITS); integrated b54e593b3da4 + 7f51a2244d15 |
| R3 | Legacy decision non-regression + public-leak freeze mirroring Energy #7895 (packet R3_nonregression) | none | SEAT-EXECUTED under Sol #7780 5814541566 §1 (rob-r3 dispatcher withdrawn: m1/mb held at active=2 by other seats' lanes since ~04–06Z) | ACCEPTED: 30bfe8d75979 (R3) → review REJECT (`foresight.score` nightly-volatile frozen) → b56ba8121ef1 (R3-fix: `foresight_decision` frozen / `foresight_score` shape, sparse guard, `PROPHET_FROZEN`, prophet top-level keys, `foresight_cascade.json` canary) → re-review ACCEPT_WITH_NITS (drift replay 0/27 red, determinism proven, 13 mutations) → 760cb4ccc8f (nits: `foresight_keys` frozen, README decisions 5/7). Baseline `frozen_at_main` 3c93f8194f6c |
| R2 | Robotics F04 composer + contract + tests over the shared envelope (packet R2_composer as run, 114 lines) | R1 accepted | mb glm-5.3 lane rs_20260924T102921Z_16517 | ACCEPTED (ACCEPT_WITH_NITS); integrated 37fd0bd35471 + guards 95d7e6ef41d7 + f257fc8e6a05 |
| R4a | Robotics partial `templates/_robotics_research_mount.html.j2` gated on the exact `robotics_automation` anchor + tests (packet R4a_partial) | T10/T10b landed on #7870 | mb glm-5.3 lane rs_20260924T101159Z_59812 | ACCEPTED (ACCEPT_WITH_NITS); integrated 31919764cf9a + f5f8e8362c5b; request 6 (ONE include line after the identity gate + T10d anchor registration) posted to the #7870 shell writer. **RULING 5 (principal, 2026-09-25): the partial is RETIRED and request 6 WITHDRAWN.** #7870's `_theme_research_mount.html.j2` was rewritten generic (no vertical named, nine-key `theme_research_mount` context, assets emitted once) and `_theme_research_section.html.j2` renders any registered vertical; `scripts/build_theme_detail.py:318` already passes the context for EVERY basket page, and `config/theme_crosswalk.yml:193` already gives `robotics_automation` exactly one primary claimant. So a Robotics-specific partial is the "copying a partial" Sol's Option A (#7780 5813801605) forbids, mine mirrored the SUPERSEDED T10b markup-carrying design, it had ZERO code referrers (verified: the only hits were its own test and this doc) so it never rendered, it re-emitted the `<link>`/`<script>` pair the shared partial now owns once, and it lacked `data-evidence-schema-id`, which the shared ENTRY partial's nine-key render gate (`_theme_research_mount.html.j2:28-33`) requires — so it could not have rendered through the shared path at all. **Leg 4 CORRECTED by independent review (R4-reg):** the original wording credited hook 4a's `mountSpecFrom`, which at `86f699b054da` had ZERO runtime call sites (its only occurrence was its own definition, inside the `THEME-RESEARCH-CONTRACT` block that only #7870's node harness executes) — so no shipped code path would have refused the partial at that head. It does now: hook 4b (`a45788878dbc`) wired it at `theme-research.js:1891-1898`. The render-gate reason above is the one that was true throughout. **A fifth and stronger leg, found by the review:** `theme_research_anchor`, the context variable the retired partial gated on, exists NOWHERE on the merged tree — so even with an include line it could never have rendered, and the deleted suite's grammar-vs-identity xfail pair is architecturally moot (one mount context per page, supplied by `mount_context_for_basket`). Robotics mounts by REGISTERING; the delta was handed to the #7870 owner at issuecomment-5826358018, and **corrected at issuecomment-5826848991**: it is not two entries but two entries PLUS three test edits (`tests/test_theme_research_registry.py:89`, `:94`, `:225` all assert `list(REGISTRY) == ["ai_semiconductors"]`; `:191` asserts `robotics_automation` is unregistered) |
| R4-reg | `engine/market_ontology/robotics_owner_bundle.py` — the `load_bundle` callable #7870's closed registration must name for Robotics, + `tests/test_robotics_owner_bundle.py` | #7870 hook 1 (`theme_research_registry`) landed | SEAT-EXECUTED (principal; Robotics-owned module, no collision) | Serves NOTHING and SAYS so: private half unbound (R4/R5), public half unowned (no declared witness cohort owns `precision_motion`/`perception`; declaring one is a Theme Graph / Data OS ruling, not this lane's). Coverage absence is a typed omission, never a 503 — `BundleUnavailable`'s own contract reserves it for a broken owner. Measured through the REAL composer: `authorized_coverage.status=unavailable`, `selected=0`, `limitations=[slice_scope_unowned]`, 0 rows, 0 evidence_refs, every authority flag false (the `degraded`/`rights_partial` pair it served until 2026-09-25 was the B2 defect, fixed in `23055bc5f89` — see the B2 section below). No loader-level `system_replay` refusal (the composer's `_refuse_unsupported_identity_vintage` already owns it, keyed on identity material that is empty here, so no request is AFFECTED). **Gate A/D suite list changed**: `tests/test_robotics_research_mount.py` retired with the partial, `tests/test_robotics_owner_bundle.py` joins — declared, not silently dropped. **INDEPENDENT REVIEW: REJECT, then integrated.** All four gates were green (A 125 / B 434 / C 0 / D 11+114 xfail, zero xpass) and mutation testing found no hole among the loader's four laws — every blocker was a FALSE STATEMENT IN A DURABLE RECORD, not a code defect. (1) The `system_replay` rationale was falsified by experiment: `_refuse_unsupported_identity_vintage` iterates `bundle.identity_results`, which this loader AND `semiconductor_owner_bundle:334,392` both hard-code to `()`, so the guard is inert for both verticals and admitting assertions would not wake it — fixed in prose and pinned by the new `test_r5_cannot_admit_assertions_without_facing_replay_vintage`, which goes red the day R5 admits owner material without either populating vintages or refusing replay. (2) "A member sees a mount that states it is serving nothing yet" was refuted on the served bytes: the client renders `degraded` as "Degraded — partial data" when there is NO data, and `rights_partial` asserts a partial ENTITLEMENT — a false commercial signal on a paid surface. Both defects were real. **The attribution was not, and it was mine:** I recorded them as shared-composer defects this lane must not fork and held live admission on "the composer owner" — a party that does not exist. `robotics_theme_research.py` is the ONLY theme-research composer on this carrier, no other `engine/market_ontology` module computes a coverage ladder, and `git log -1 -L 1155,1170` attributes the ladder to this operation's own R2 commit `37fd0bd35471`. **Fixed in lane** at `23055bc5f89` (see the B2 section below); the omissions still stay, because dropping them would buy an honest "Unavailable" by discarding the diagnosis of which half is absent. (3) Leg 4 of RULING 5 corrected — see the R4a row. Nits 3/4/5/6 folded: the emptiness-predicate test is relabelled a control and not counted as loader coverage; `test_coverage_absence_is_never_a_refusal` no longer duplicates the rights-revision assertion and now exercises all five views × three time modes; the owner-plane grep is relabelled a defeatable drift tripwire; and the "tests exercise both resolutions" claim is withdrawn (only the local mirror is reachable today). Post-integration: **gate D 20 passed / 115 xfailed, zero xpass** |
| R7 | Source-rights qualification matrix + proposed narrowly scoped registry/prefix change (rights_class unresolved) for adjudication (packet R7_rights_matrix) | Sol #7780 5814333887 | SEAT-EXECUTED under Sol §1 (rob-r7 dispatcher withdrawn; remote rob-r7 worktrees removed) | ACCEPTED: v1 review REJECT (7 blockers) → v2 ACCEPT_WITH_NITS (8 nits taken) → committed 62bce5afef2a (`research/theme_graph/thematic_research_20260924/ROBOTICS_SOURCE_RIGHTS_QUALIFICATION_2026-09-24.md`: 15 rows, 11 proposed families all `unresolved`, refusal behaviour, Q1–Q4/G1–G4); qualification return posted to Sol #7780 issuecomment-5815643294 (14:04Z). Pending = refused until Sol adjudicates |
| R2b (+R2c) | Canonical theme-id re-grounding of the R1 corpus, composer match via the identity owner (`scope_slug_keyed:<n>`), R1 nits n1-n3, R2 nits N1/N2/N4/N5/N6/N7/N9/N11/N12/N13, Sol addenda S1 (`identity_vintage_unsupported`) + S2 (`slice_scope_unowned` cohort); R2c = interpretation blocks whose `input_revisions` are absent from the bundle are WITHHELD (`interpretation_inputs_absent:<n>`), Sol 5814333887 §4 | R2 accepted (done); #7870 5812295091 | SEAT-EXECUTED under Sol §1 (rob-r2b dispatcher withdrawn; remote rob-r2b worktrees removed); review tree `seat-rob-r2b` = carrier + #7870 3e3a7956d014 | ROUND 12 ACCEPT, ZERO BLOCKERS, six nits (nit 1 `import re` dead → fixed in 3d73de31e21; nits 2-5 were five wrong counts of MINE, corrected in that commit message; nit 6 accepted as-is by ruling). The reviewer proved it two ways: a TOTAL static proof (fix11 `_ownership_role` reads only `predicate`, `statement_mode` and `temporal.business_valid_from`, uses zero module globals, has four reachable returns, and the strings `announced_seller`/`announced_acquirer` do not occur in the function — covering the infinite input space, not a sample) and a 536,448-case dynamic differential through the real entry point with 27,132 directional sides as positive control at the parent: fix11 produced ZERO. Cohort diff reproduced exactly (305 rows, key set identical, exactly 10 change, only `companies` differs across 100 composed responses); 5 of 6 new/changed tests fail against the parent; a reintroduced one-line direction fails 5 tests (teeth proven); all 28 inversion triples verified truthful to their round labels, with exactly the 14 `r11-*` entries still inverting at fix10; all 19 deleted names at zero references; no missed pin or consumer (the frontend reads `role` only as an ARIA attribute and `compose_robotics_research` has no non-test caller) |
| R4b | Facet rendering / per-anchor Theme Tracker entry on the generic client | Sol build-out ruling (#7780 5811066300) + T10c/T10d | remote lane | held |
| R5 | Real evidence qualification through the shared admission/private adapter | R4 ruling live proof | seat + helper | held |
| R6 | Browser/deployed proof, EN/ZH, dark/light, mobile, mirror probes | R2/R4/R5 + deploy | seat + helper | held |

## Robotics mount registration values — the canonical copy

RULING 5 retired this lane's mount partial, and Sol's Option A puts a vertical's mount strings
in the shared owner's import-light leaf (`engine/market_ontology/theme_research_mounts.py`,
closure 2 files) where they are hand-typed. The consequence, found by the R4-reg coverage
audit: **three of the nine values live in no source file in either repository** — they existed
only in the deleted partial and in PR comment `5826358018`. Recorded here so they survive the
PR. Four identity values are recoverable from `robotics_theme_research.py:55,56,58,72`; both
`note_*` strings are byte-identical to semiconductor's.

| field | value | recoverable from |
|---|---|---|
| `anchor_theme_id` | `robotics_automation` | crosswalk + composer |
| `slice_keys` | `("precision_motion", "perception")` | `robotics_theme_research.SLICES` |
| `schema_id` | `robotics_theme_research.v1` | `robotics_theme_research.SCHEMA_ID` |
| `evidence_schema_id` | `robotics_theme_research.evidence.v1` | `robotics_theme_research.EVIDENCE_SCHEMA_ID` |
| `slice_labels["precision_motion"]` | `("Precision Motion", "精密运动")` | **THIS FILE ONLY** |
| `slice_labels["perception"]` | `("Perception", "感知")` | **THIS FILE ONLY** |
| `title_en` | `Robotics industry research` | **THIS FILE ONLY** |
| `title_zh` | `机器人产业研究` | **THIS FILE ONLY** |
| `note_en` | `Paid research context for members. Nothing here ranks, gates, sizes or times anything.` | identical to `_SEMICONDUCTOR` |
| `note_zh` | `会员研究内容。此处内容不构成排序、准入、仓位或时机判断。` | identical to `_SEMICONDUCTOR` |

Every value above was read back from the handover comment body, not written from memory. That
check mattered: a first draft of this table had `Precision motion` (wrong case) and an invented
`("Perception & sensing", "感知与传感")` where the delta says `("Perception", "感知")`. A canonical
copy transcribed from memory is worse than no canonical copy — if the shell owner had typed this
table, the registration would have drifted from both the delta and the composer on day one.

## Shared-shell state at #7870 `17b72317b737` — one live gap, reported and now CLOSED at `6cd958e92b2`

Hook 4b landed (`a45788878dbc`, "one client instance per mount"), which closes the label half:
`theme-research.js:1891-1898` now builds a spec from all seven mount attributes and `:1401`
resolves slice labels from `SPEC.labels`, so Robotics labels will render from the registration
rather than the client's own map. Two corrections to earlier claims in this file's lane records
follow from reading the CURRENT head rather than a pin: `mountSpecFrom` had no runtime caller at
`86f699b054da` and has one now, and `data-evidence-schema-id` was read by nothing and is read now.

**Still semiconductor-only, and it is a real defect for any second vertical** —
`theme-research.js:1054`:

```js
if (sel && TR_SLICE_KEYS.indexOf(sel.slice_key) >= 0 &&
    SLICES.indexOf(sel.slice_key) >= 0) currentSlice = sel.slice_key;
```

`TR_SLICE_KEYS` is still `['hbm_packaging','sic_gan_specialty']` (`:112`), so for Robotics the
conjunction is unsatisfiable and a **valid** stored slice selection is silently discarded on
restore — which contradicts the comment six lines above it ("the slice vocabulary that validates
it is this mount's, not a list compiled into this file"). `SLICES` is the correct mount-scoped
check; the `TR_SLICE_KEYS` conjunct is the leftover. ~~`TR_VIEW_KEYS`/`TR_MODE_KEYS` in the same
block are genuinely generic (this vertical's `VIEWS` tuple is identical to `:113`) and must stay.~~

**The `TR_VIEW_KEYS` half of that sentence is FALSIFIED** — by Technology, the third vertical
(issuecomment-5827349789), and conceded at issuecomment-5827367115. My evidence was that this
vertical's `VIEWS` tuple is identical to `:113`; it is identical **because it was adopted from
semiconductor** so one route and client serve both (`robotics_theme_research.py:7` says exactly
that), not because the list is generic. Two verticals agreeing where the second copied the first
is a sample of one, and I generalised from it in a durable record that the shell owner then acted
on. Technology's own view tuple has ZERO overlap with `:113`.

Measured from the registration side, which is this lane's to measure: `MountFacts` carries
`slice_keys` and `slice_labels` and **no view field of any kind**, and `mount_context` emits
exactly nine keys — `anchor_theme_id`, `slices`, `schema_id`, `evidence_schema_id`,
`slice_labels_json`, `title_en/zh`, `note_en/zh`. So unlike the slice case there is no
mount-scoped counterpart to fall back on: `data-slices` exists, `data-views` does not. The view
half is a mount-contract change, not a JS edit. `TR_MODE_KEYS` is untouched by this correction —
the three time modes are the shared research-mode vocabulary, and nothing has falsified that.
~~`parseStoredSelection` (bare, `:118`) now has no callers, so it can go with the conjunct.~~
**That sentence is wrong and was corrected to the owner at issuecomment-5827344619:** `:126`
uses `TR_SLICE_KEYS` inside `parseStoredSelection`, which #7870's own node cases drive directly
and whose `test_..._ui.py:2199` pins that the WIRING must never call it. It is a deliberate
test-only helper living in the contract block, not dead code — so the fix is the conjunct alone.
Reported to the shell owner at issuecomment-5826848991. **This is shell work**, which retracts
this lane's earlier "Robotics' remaining gap is not shell work".

**CLOSED 2026-09-25 at `6cd958e92b2`** ("a second vertical's remembered tab now comes back").
Verified by this lane as the only second vertical that can: the conjunct is gone and `SLICES`
stands alone; `test_a_second_verticals_remembered_slice_actually_restores` drives
`beta_slice` — a key in no version of `TR_SLICE_KEYS` — behaviourally through a real boot,
seeded localStorage and a chip click, asserting NO write; its premise holds (`:1405` is
`if (currentSlice === key) return;`); and it carries its own positive control proving the probe
can see a write at all. `test_the_wiring_never_consults_one_verticals_slice_list` closes the
class rather than the instance, and is satisfiable because `TR_SLICE_KEYS` sits in the contract
block ahead of `/* THEME-RESEARCH-CONTRACT-END */`.

## Honest import closure of the loader (corrects the #7870 handover §4)

The handover said `robotics_theme_research` is "stdlib-only at module scope plus
`engine.theme_graph.curation_assertion`". That understated it: the module also has a guarded
module-scope import of `semiconductor_theme_research` (`:123`) which pulls
`engine.company_intelligence.*`, and `curation_assertion` pulls `jsonschema` + `attrs` /
`referencing` / `rpds`. Measured closure is **145 modules** for `robotics_theme_research` and
**146** for `robotics_owner_bundle`, the difference being exactly
`engine.market_ontology.robotics_owner_bundle`. The conclusion still holds and was verified with
#7870's own probe: `FORBIDDEN_LOADED=[]`, with positive controls firing on `numpy`, `requests`,
`jinja2` and `engine.neuralweb.company_intelligence_reader`.

## B2 — the gate this lane held on itself (`23055bc5f89`, 2026-09-25)

R4-reg blocker B2 was recorded as two **shared-composer** defects with live admission held until
"the composer owner" fixed them. There is no such owner. Measured three ways before acting:

| instrument | result |
|---|---|
| `ls engine/market_ontology/*theme_research*` | `robotics_theme_research.py` is the ONLY theme-research composer on this carrier |
| `grep -rln coverage_status engine/ scripts/` | four unrelated subsystems + my file; no other ladder under `engine/market_ontology` |
| `git log -1 -L 1155,1170` | the ladder is `37fd0bd35471`, **this operation's own R2 commit**, created from `/dev/null` |

Both defects were real; only the attribution was wrong. Fixed in lane:

- **Emptiness outranks omission.** `degraded` is the PARTIAL state and the client renders it
  "Degraded — partial data"; an omission never ADDS data, so it can never lift an empty read
  above `unavailable`. `authorized_coverage.selected` is `len(selection.assertions)` seven lines
  below, so the status and the count can no longer disagree.
- **`rights_partial` needs a selection to be partial ABOUT.** The v1 schema's own description
  reserves the token for rights partiality; neither omission is a withholding
  (`private_assertions_unbound` = unbound store, `public_cohort_unowned` = undeclared cohort);
  and the client renders limitation slugs **verbatim** (`:1599`, `textSafe` is escaping only), so
  the raw token was the member-facing sentence asserting cut entitlements on a paid surface.

The loader's omissions **stay on the bundle** — dropping them would trade the which-half
diagnosis for a cosmetic fix. The composer simply no longer turns them into a member-facing claim.

**Deliberate consequence, now pinned:** the served payload for an empty bundle is byte-identical
to one composed with `omissions=()`. Measured before the fix, the two differed in exactly two
fields across all five views and nothing else leaked. So an empty read can no longer disclose
*that withheld content exists* — the disclosure RBV-27 exists to prevent. Pinned by
`test_rbv27_the_response_never_names_a_withheld_family` (both named fields + whole-payload
identity); its positive control is `test_rbv27_rights_partial_never_names_families`, extended
with a zero-selection leg on the corpus's own `later_retained_backdate` case.

Blast radius, all 20 loadable fixture cases composed as shipped and with a synthesized omission:
19 cases `sel>0, omis=0` unchanged; the RBV-27 manoeuvre unchanged; `later_retained_backdate`
(`sel=0, omis=0`) unchanged. **Only `sel=0, omis>0` changes.** Zero RBV cases weakened.

Gates A 135 / B 622 / C exit 0 / D 20 passed + 115 xfailed, zero xpass — all at the recorded
baseline. Run wider (adding the theme-graph foundation) gives 941 passed / 3 failed, all three in
`tests/test_theme_graph_identity_resolution.py` on a 2807-vs-2806 company-node pin; reverting
this lane's four files to `HEAD~1` in place reproduces them identically, so they are pre-existing
and are the identity plane's acceptance evidence (independently reported at #7780 5827208326 §6).

Recorded at #7908 issuecomment-5827273049.

## Mount registration — PROVEN on a merged tree, and the sequencing ruling

The delta was "paste-ready" but never executed. It is now executed and measured, on #7870's
**current-head** `theme_research_mounts.py` + `theme_research_registry.py` dropped onto the merge
worktree with the two Robotics entries applied:

```
REGISTRY keys      : ['ai_semiconductors', 'robotics_automation']
registration_for   : robotics_automation  robotics_theme_research.v1  2026-09-24.1
allowed_slices     : {'precision_motion', 'perception'}
mount_context      : nine keys, all non-empty; slices = precision_motion,perception
slice_labels_json  : {"perception":["Perception","感知"],"precision_motion":["Precision Motion","精密运动"]}
served (through the registration's OWN load_bundle + compose):
  schema robotics_theme_research.v1 · definition_version 2026-09-24.1 == registration
  authorized_coverage.status unavailable · selected 0 · limitations ['slice_scope_unowned']
  every authority flag False · byte-identical to omissions=()
```

**The delta's shape changed under this lane:** both modules now build from an `_ENTRIES` tuple
with an `_assert_unique_anchors` load-time guard, so the edit is a `MountFacts` block plus
`(_SEMICONDUCTOR, _ROBOTICS)` — not an edit to the `MOUNTS` comprehension the earlier delta
described. The registry half needs an eager import aliasing `select_authorized_evidence` (my
selector shares semiconductor's name) and a lazily-bound `_load_robotics_owner_bundle` wrapper.

**Exactly three tests go red, four sites** — `test_registry_is_a_read_only_mapping_with_exactly_one_entry`
(`:89`, `:94`), `test_synthetic_registration_constructs_without_touching_the_registry` (`:275`),
`test_registration_for_unknown_or_non_exact_probe_is_none[unregistered-real-theme]` (`:241`→`:249`).
A fourth failure in my run (`semiconductor_owner_bundle` ModuleNotFound) is an artifact of the
merge worktree pinning a #7870 older than the registry/mounts refactor — declared, not reported
as a consequence. Trap recorded for whoever edits `:241`: `robotics_automation` remains the
correct *foreign-anchor* negative in `test_..._ui.py:1659/:1666/:1697`.

**Trap — label order.** `mount_context` serialises `slice_labels_json` with `sort_keys=True`, so
Robotics' key order is alphabetical (`perception` first), not `slice_keys` order. Set equality
holds. Semiconductor's two keys are already alphabetical, so an order-based assertion written
against it would pass today and fail the day Robotics lands.

**RULING 6 (principal, 2026-09-25) — the registration is POST-MERGE.** `compose` and
`select_evidence` are bound by *eager* module-top import in `theme_research_registry.py` (only
`load_bundle` is lazy), so a Robotics entry imports `robotics_theme_research` at registry-import
time, which does not exist on #7870's branch. The order is: #7908 merges → the shell owner lands
the registration. This lane does **not** add it from this carrier (#7870's paths), and does not
ask for it early. The proof above exists so the values and the binding are known-good before they
first enter their tree. Independently agreed by the semiconductor seat at #7780 5827208326 §7;
verified here rather than taken. Posted at #7870 issuecomment-5827332885.

## The carrier's CI red was my own YAML, and two of the three failures were never failures (`e9d5be2748c`, 2026-09-25)

Recorded at #7908 issuecomment-5827488856.

`fence-pack` and `self-mod-fence` had been red on this carrier since before the B2 fix —
the pre-B2 head `87ad72e9dd31` carries the identical three verdicts and `main` at
`9051eab960a` is green on both, so it was neither B2 nor base drift.

**The one genuine failure was mine.** `scripts/agentos.py validate` emitted 12 hard
`bad-changed-entry` errors against this file: every `changed:` entry was a bare `- path:`
with no `what:`, and the single `what:` in the block attached by YAML to the LAST entry
rather than the first one it was written for. The block was also UNTRUE — it omitted four
paths this carrier changes (R7, the non-regression baseline + README, the non-regression
battery) and still listed the two paths RULING 5 retired. The machine-readable header was
advertising the duplicate mount plane after the prose had struck it through. Now 14 entries
accounting for all 35 changed files, nothing unaccounted. `validate`: 12 errors before,
0 after, same command and file — which is also the positive control that the checker has reach.

**Two traps that cost probes and will cost the next reader the same.**

* `templates/chat.html's header no longer matches _site_nav.html.j2` is emitted by
  `scripts/sync_chat_nav.py --selftest` as its OWN positive control. The next log lines are
  `FIXED:` and `selftest PASS: drift detected, --fix heals both copies`; the real invocation
  prints `chat nav sync OK`. GitHub scrapes `::error::` from stdout regardless of exit
  status, so a PASSING self-test publishes an annotation telling the reader to hand-edit a
  GENERATED file, on PRs that touch no template at all. **Falsifier:** run
  `python3 scripts/sync_chat_nav.py` with no flags on this tree — `chat nav sync OK`, rc 0.
  **So what:** an annotation is not a verdict. Read the job log around it before believing it.
* The three `self-mod-fence: ... fail-closed` lines are the step's SOURCE echoed in the
  `##[group]Run` header, not its output. That step passed. `self-mod-fence` is a composite
  whose summary read `success, success, success, failure`; the failing member was the
  agentos validation above.

**The remaining red is not a carrier defect.** `ci-authority/codex/merge-queue-pilot` reports
`allowed: true`, `reason: ordinary_change`, `authority_hit_count: 0`, failing only on
`context_active: false / inactive_base_context` — it is scoped to base ref
`codex/merge-queue-pilot` and this carrier's base is `main`. GitHub's `mergeable_state` for
#7908 is `unstable`, not `blocked`, i.e. mergeable with a non-required check failing.

**B2 is not yet proven.** I authored both B2 lines, so builder != reviewer forbids me from
closing it. A READ_ONLY independent review of `23055bc5f89` is commissioned with an
adversarial brief (own byte-identity probe, reachability enumeration of the coverage states,
strongest case AGAINST the suppression ruling, mutation of both edited lines). B2 stays
unintegrated-as-proven until it returns and I adjudicate.

## RULING 7 — the carrier's HOLD gated itself; it gates release, not merge (#7908 issuecomment-5827514263, 2026-09-25)

The carrier's own description said "Draft/HOLD: no merge, no label, no release until the
master packet's completion law is met." That is circular. Completion criteria 2 and 7 require
the existing Theme Tracker and `basket/robotics_automation.html` to SHOW the paid research
result; that needs the mount registration; and RULING 6 places the registration after this
carrier merges, because `theme_research_registry.py` binds `compose` and
`select_authorized_evidence` by EAGER module-top import. Merge <- completion <- page <-
registration <- merge. Two completion criteria were unreachable and the HOLD held against itself.

**Checked against the packet's text, not my summary of it.** The packet never forbids merging
this carrier. Its §3 anti-criteria end "The mission is not complete when ... a PR merges" —
merge is INSUFFICIENT, not forbidden. Line 180's "do not merge automatically" is about #7773,
the packet PR. Line 473 constrains CHILDREN. Line 594 says "do not treat CI/merge as product
acceptance." And the Chairman's closing charge, line 661, says "Do not stop at infrastructure,
CI, merge or a partial page" — which presumes the mission passes THROUGH merge. The law is
merge-is-not-acceptance, and the carrier body over-read it into completion-precedes-merge.

**Ruling.** The HOLD gates label, release, live admission and any MISSION_COMPLETE claim.
Merge becomes permissible only on all four of: exact-head gates A/B/C/D at baseline;
independent review passed (completion-law item 6 — the item that genuinely gates merge);
the non-regression freeze holding (item 5); and CI green apart from
`ci-authority/codex/merge-queue-pilot` (`allowed: true / ordinary_change`, failing only on
`inactive_base_context`). Merging is NOT a completion claim — criteria 1, 2, 3, 4, 7, 8 stay
open after it and live admission stays exactly where it was.

**Consequent ordering, simpler than RULING 6 first implied.** #7908 merges FIRST. #7870 is
`dirty` against main and must rebase anyway; rebased onto a main that already carries
`robotics_theme_research.py`, it can register BOTH verticals in its own registration, eagerly,
with no dangling module reference and **no third follow-up PR**. Rejected alternative: making
`compose`/`select_authorized_evidence` lazy so registration could land first — it would put a
registry entry for a non-existent vertical on main between the two merges, and would mean
editing the shell owner's module for ordering convenience alone.

**Falsifier.** If the packet owner intends "no merge until completion law" literally, this
ruling is wrong — and then criteria 2 and 7 are unreachable as specified and the packet needs
an amendment, because no ordering of merges satisfies both. Nothing is merged on this ruling
today: the independent-review gate is open.

## Merge gates 1 and 3 discharged against CURRENT main, which had drifted 190 commits (`6f434112736`, 2026-09-25)

RULING 7 named four merge gates. Two of them are now measured rather than assumed.

The carrier's base is `3c93f8194f6` and `origin/main` is `9051eab960a` — **190 commits of
drift**, and the recorded gates A/B had only ever been run over a merge with #7870's branch,
never against a current main. That gap was real and nobody had closed it.

Merge worktree `rob-mainmerge-gate` = `origin/main` `9051eab960a` + carrier `0c59f914a75`
→ **`6f434112736`, zero conflicts**.

* **Gate C** `scripts/check_theme_graph_contracts.py` → **exit 0** (census: company nodes 2807,
  projection rows 2807 — the same pin as before, so the 2807-vs-2806 disagreement is not
  reachable from this merge).
* **Gate D** the six Robotics batteries, strict xfail → **20 passed, 115 xfailed, zero xpass**,
  exactly the recorded baseline.

**The per-file split is the part worth keeping, because the aggregate hides it:**

| battery | on main alone |
| --- | --- |
| `test_robotics_theme_non_regression.py` | **9 passed, 0 xfailed** |
| `test_robotics_research_inputs.py` | 11 passed, 4 xfailed |
| `test_market_ontology_robotics_theme_research.py` | 37 xfailed |
| `test_robotics_research_composition.py` | 35 xfailed |
| `test_robotics_research_temporal.py` | 17 xfailed |
| `test_robotics_owner_bundle.py` | 22 xfailed |

So **merge gate 3 (the non-regression freeze) is genuinely discharged** — those 9 run and pass
against current main with the carrier applied; the freeze is not hiding inside an xfail. Had
they xfailed, "gates green" would have been hollow and the freeze unchecked, which is why the
aggregate number is not sufficient evidence on its own.

The four composition/loader batteries are **100% xfail on main alone** (111 of the 115). That
is by design and is the honest state: merging this carrier puts 111 armed tests on `main` that
exercise nothing until #7870's shared foundation lands. They are **strict** xfail and gate D
records **zero xpass**, which is the check that every one of those markers is honest today —
and when the foundation arrives, any that would pass will XPASS and fail the build, forcing the
markers off rather than letting them rot.

Remaining merge gates: **2 (independent review of B2 — in flight, builder != reviewer)** and
**4 (CI green apart from the `inactive_base_context` pilot — currently satisfied)**.

## Completion criterion 4 (public mirrors) — merging this carrier adds NO public-mirror surface. Measured, not asserted.

`gh api repos/.../macro --jq .private` → **`false`**. The repository is **public**, so this
repo's known leak class is live: anything materialised under `site/` is retrievable
unauthenticated from raw.githubusercontent.com. That makes the question worth measuring before
merge rather than at admission.

* **The carrier writes nothing under `site/` or `premiumdata`.** `git diff --name-only
  origin/main...HEAD | grep -E '^site/|premiumdata'` → empty. The single `site/` string in the
  composer is a comment naming the client that renders the status.
* **Neither the composer nor the loader performs any read.** No `open(`, `read_text`,
  `read_bytes`, `urlopen`, `requests.` or `boto3` in either module. `load_robotics_owner_bundle`
  takes `query` and an optional `rights_snapshot` and reads NOTHING from the query — not a
  slice, path, URL, locator, event id, ticker or CIK — so it has no byte source of its own and
  cannot be a leak vector. The private binding lives in the SHARED adapter (T11), not here.
* **The fixture corpus is synthetic under measurement, not under its own label.** I wrote the
  "synthetic throughout" line myself, so I measured it instead of citing it: 21 fixtures,
  **zero** redistribution-shaped keys (`body`, `full_text`, `article`, `content`, `raw`, `html`,
  `excerpt`), and the longest string value in the entire corpus is **235 characters** — analytic
  prose the lane wrote (`limitations.coverage`, `expected_regression`), not a quoted source
  body. The one quoted fragment is the deliberate injection sentence inside
  `source_authority_injection.json`, which is the adversarial case's payload.

**What this does NOT establish.** Criterion 4 is *not* discharged. It asks that anonymous, free
and public mirrors cannot recover full-fidelity CURRENT research — and the real research payload
arrives through the shared private adapter and the shared paid API, neither of which is mine and
both of which are held (R5). What is established is narrower and is a **merge-safety** statement:
merging #7908 cannot create a new public-mirror surface, because this carrier ships no served
bytes, no reader and no real research. The public-mirror probe itself remains owed at admission.

## "Preserve all 32 RBV cases" — measured. 28 cited on the carrier; the other 4 accounted for individually, not waved through.

The packet's §10 acceptance checklist requires "all RBV-01 … RBV-32 acceptance cases mapped".
I had been repeating "the 32 preserved RBV cases" without ever measuring it, so I measured it.

The carrier's own 35 files cite **28 distinct RBV ids**: RBV-01..12, 15..28, 31, 32.
**Absent: RBV-13, RBV-14, RBV-29, RBV-30.** Instrument control: a case-insensitive search for
`rbv[ _-]?(13|14|29|30)` across the same files returns nothing, so the absence is real and not
a spelling miss; and `precision_motion` hits 18 files, so the search has reach.

Each of the four, resolved against the approved plan's traceability table (`plan.md:966-967`)
and the spec:

* **RBV-13** — "K1 cross-type joins without a consumed valid bridge refuse/degrade." Plan maps
  it to **Task 3**, and the packet's own amendment (line 45) says Task 3 is the K1 curation
  subtype, **SHARED / IN FLIGHT on #7870**, with "Robotics consumes the accepted result; **no
  Robotics-specific K1 subtype**". Correctly absent here. Theirs to map, and I am forbidden to
  build it.
* **RBV-14** — "Do not substitute the registered QLedger forward-claim object for factual
  product evidence." Plan maps it to Tasks 3 **and 4**, and Task 4 is my composer. **I was
  heading toward reporting this as an unmapped gap in my own lane, and that was wrong.** The
  spec's only mention of QLedger is in **rejected alternative B**: *"put factual bodies in
  K1/QLedger. Rejected. … the registered QLedger object is a forward claim."* RBV-14 is a
  **negative** acceptance case — it asserts the rejected alternative was not built. The absence
  of QLedger from my code IS the compliance, not a hole in it.
  **Now measured rather than argued:** importing both Robotics product modules pulls in **145
  modules, of which ZERO are QLedger** (`engine/qledger.py`, `qledger_desk_adapter.py` and
  `qledger_evidence_clock.py` all exist, so the term is real and reachable in principle). The
  only `engine.theme_graph` members in the closure are `theme_graph` and
  `theme_graph.curation_assertion`.
  **The one real gap: nothing ASSERTS that absence.** A negative case satisfied by construction
  is exactly the kind that regresses silently the day someone adds a convenient import. Owed:
  one import-guard test pinning that the Robotics composer and loader reach no `qledger` module.
  Cheap, mine, and queued behind the in-flight B2 review (no code changes while it runs).
* **RBV-29** — "Unauthorized/forbidden/error responses preserve incumbent auth and
  private-no-store behavior." §6, the shared paid API boundary (Task 5 / T09). Not mine; held.
* **RBV-30** — "Desktop/mobile, EN/ZH and dark/light preserve identical quantities, units,
  statuses and sources." §6. **This case IS R6**, the browser proof, and it is completion-law
  item 7. Held on the mount registration, which RULING 6/7 place after this carrier merges.

So the 32 are accounted for: 28 instrumented here, 1 shared (13), 1 satisfied-by-construction
with an owed guard test (14), 2 held in named lanes (29 = shared API, 30 = R6). None silently
dropped, and none marked covered on the strength of a matrix row.
