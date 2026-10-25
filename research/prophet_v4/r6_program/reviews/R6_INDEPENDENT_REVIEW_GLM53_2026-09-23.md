# R6 independent external review — Prophet US handoff delta

Reviewer: GLM-5.3 (independent external reviewer). Seat: Fable Meta-CEO.
Operation: `prophet-us-fable-meta-ceo-20260923-001`. Date: 2026-09-23.

## DISPOSITION

**ACCEPT_WITH_REPAIRS.** The governance delta is a coherent, bounded transfer of Prophet US program accountability to Fable: it removes mandatory Astra/Sol decision returns without removing independent review, incumbent technical ownership, scientific promotion, source custody, runtime admission, rights, budget, release, or reserved Chairman authority. The effective plan and branch gates preserve sleeve-specific horizons and reject invented anchors, universal scores, date relabeling, and native-agent fallback. One integrity defect blocks baseline adoption as delivered: the packet's first instruction is to run `verify_handoff.py`, but the committed source omits `archives/R5_source_packet.zip` while its verifier and manifest require that file. The PR body discloses the omission, not the resulting verifier failure. The smallest repair is either to supply the exact archive and its canonical Agent OS record in the locations the manifest defines, or to amend the packet/verifier/manifest/entry instructions coherently so verification proves exactly the committed bytes; do not weaken verification merely to turn this red result green.

## REVIEWED

- PR: mastermindx-market-intelligence/macro#7809, branch `claude/prophet-us-r6-meta-ceo-adoption`, reported and local head `f98e72fb2a57c25f528d7c585a4632ac0a3a2b6c`.
- PR snapshot: title, body, reported head, file list, draft state, and bounded diff; 111 files changed when compared with `origin/main`.
- Six core document digests (`git hash-object`):
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/SUPERSESSION_MAP.md` — `3e7e8ca39d0899ccd888adc5c05afafb12a1b641`
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/FABLE_META_CEO_EXECUTION_HANDOFF.md` — `546234d125d7562b5d98c9f03537b870f5bc969e`
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/FIRST_WAVE_RUNBOOK.md` — `cc6d8b54f17e72bd2287aad98b028729cbc7920f`
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/DECISION_RESOLUTION_PLAYBOOK.md` — `cf00d396d42c28af90b0b7b792665191f92defd0`
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/ACTIVATION_GATES.json` — `70bd61aaa99daab7d7d17207a61b8a5df62095c2`
  - `research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.md` — `a5dcc6b2cee2b5e65a0dbde844eed074a313f1db`
- Read in full: `INDEPENDENT_REVIEW_BRIEF.md`; the six core files above; `effective/RESEARCH_DOCKET.md` Q01–Q06; `EXTERNAL_FABRIC_POLICY.json`; `AUTHORITY_DELEGATION.json`; `agentos/decisions/DEC-PROPHET-US-FABLE-META-CEO-DELEGATION.md`.
- Read selectively against the twelve required challenges: `START_HERE.md`, `FABLE_START_PROMPT.md`, `HANDOFF_STATUS.json`, `R6_SOURCE_REFERENCES.json`, `R6_HANDOFF_ACCEPTANCE.json`, `effective/START_HERE.md`, `effective/ACCEPTANCE_CATALOG.json`, `effective/BUILD_PROGRAM.json`, `effective/RESEARCH_DOCKET.json`, work cards B00–B07/B20 and Q01/Q05, and the R5→R6 master-plan delta.

## BLOCKING FINDINGS

### B1 — The committed packet cannot execute its own mandatory first verification step

**Citation:** `START_HERE.md:9` says to run `python verify_handoff.py`; `FABLE_START_PROMPT.md:5` repeats that instruction. `verify_handoff.py:131` unconditionally reads `archives/R5_source_packet.zip`, hashes it at lines 132–139, and later requires every manifest path at lines 163–171. `MANIFEST.json:77-80` lists that archive. The PR body says the archive was deliberately omitted while preserving its 28 members under `baseline_r5/`.

**Counterexample:** On the exact PR head, from the packet directory, `python3 verify_handoff.py` exits 1 with `HANDOFF VERIFICATION FAILED: [Errno 2] No such file or directory: '.../archives/R5_source_packet.zip'`. An independent byte check found 108 of 110 manifest entries present at the expected size and SHA-256; the missing entries are that zip and the packet-local copy of the canonical Agent OS decision. The latter is present outside the packet at `agentos/decisions/DEC-PROPHET-US-FABLE-META-CEO-DELEGATION.md` with the exact manifest digest.

**Effect:** The reviewer and intended Fable receiver cannot establish the packet's advertised exact-byte baseline by following the packet's own first instruction. This also makes the PR body's local-proof wording stale for the committed head and risks a receiver improvising around a integrity-check failure.

**Smallest repair preserving the job:** Prefer restoring both manifest entries exactly, making the deliberate handoff bytes self-verifying and the canonical Agent OS record the same bytes. If repository policy forbids those duplicates, instead change only the packet contract: remap the canonical record to its real path, replace zip verification with byte-equivalent verification of all 28 preserved members plus the recorded archive digest as provenance, update the manifest census, and correct every entry instruction and PR claim. Any repaired verifier must still fail on a changed baseline member.

## NONBLOCKING

### M1 — B00 retains a potentially confusing legacy technical-owner label

**Citation:** `effective/BUILD_PROGRAM.md:29` and the machine mirror `effective/BUILD_PROGRAM.json:22` call B00's technical owner “Sol program owner with independent reviewer”, while `effective/BUILD_PROGRAM.md:3` and `FABLE_META_CEO_EXECUTION_HANDOFF.md:16-18` make Fable accountable and make Astra/Sol program approval nonmandatory.

**Counterexample and assessment:** Read in context this denotes an incumbent technical/source owner, not a required CEO approval; `effective/PROPHET_US_MASTER_PLAN_R6.md:730` requires review through “the existing owner.” No `requires_astra` flag is true, and no effective card requires an Astra research session or final review. The label nevertheless invites a future worker to re-create a Sol gate, especially because `effective/BUILD_PROGRAM.md:9` already says the source path requires the current writer gate.

**Effect:** Ambiguity only; it does not itself restore a prerequisite. **Smallest repair:** rename B00's technical owner to the concrete current documentation/source owner (or “existing program documentation/source owner with independent reviewer”) in both representations, without changing custody.

### m1 — Verifier PASS is correctly bounded, but its communications should remain non-authoritative

**Citation:** `START_HERE.md:9`, `FABLE_START_PROMPT.md:5`, and `verify_handoff.py:174-178` describe the check as local document/hash/graph/responsibility validation only and report zero product or operating acceptance tests. The review found no effective document or card treating PASS as scientific, runtime, source, release, or product proof.

**Effect:** None now. **Smallest improvement:** continue to quote the verifier's scope wherever its output is copied, and never use PASS as a substitute for the independent review and owner adoption required by `FIRST_WAVE_RUNBOOK.md:5-14`.

## REQUIRED CHALLENGES

1. **Residual mandatory Astra/Sol prerequisite — FOUND as ambiguity M1, not a substantive prerequisite.** I searched all effective markdown/JSON and work cards for required Astra/Sol sessions, approvals, final reviews, true `requires_astra`, and HOLD-FOR-SOL dependencies. Every B/Q owner returns to Fable; historical HOLD-FOR-SOL is closable after real gates; technical/source owners remain. B00's “Sol program owner” label is the only potentially misleading residue.
2. **Implicit native-agent fallback — NOT FOUND.** `FABLE_META_CEO_EXECUTION_HANDOFF.md:54-64`, `EXTERNAL_FABRIC_POLICY.json:5-23`, effective master sections 21.2–21.3, and every sampled card prohibit built-in/native children, wrappers, nested descendants, and internal fallback. Capacity loss holds the affected child lane; only already-approved external routes or safe principal judgment may continue.
3. **Unbounded Fable routine implementation — NOT FOUND.** `FABLE_META_CEO_EXECUTION_HANDOFF.md:66-70` permits only a bounded hardest residual or intrinsically principal decision, with record, scope, stop condition, and review; routine work returns externally. Effective Q cards use the same bounded-principal exception wording.
4. **Imaginary runtime/provider API — NOT FOUND.** The exhaustive `fabric.*` / `executive_*` / `submit_ceo_intent` search found: `EXTERNAL_FABRIC_POLICY.json:21`, explicitly forbidding invented `fabric.*`; and `FABLE_META_CEO_EXECUTION_HANDOFF.md:60`, naming the five Executive ingress tools (`executive_state`, `executive_inbox`, `executive_job`, `ceo_intent_status`, `submit_ceo_intent`) only as architecture references, expressly not proof of mounting or production readiness, and requiring inspection of the actual accepted surface/schema. No text treats any endpoint, socket, credential, or request field as proven.
5. **Undocumented takeover — NOT FOUND.** `FABLE_META_CEO_EXECUTION_HANDOFF.md:50-52`, `FIRST_WAVE_RUNBOOK.md:3,16-34,38-52,74`, and work-card ordered execution require reconciling incumbent writers, exact heads, reviews, START/RUNNING, and EFFECT_UNKNOWN state before binding; Meta-CEO accountability does not seize a carrier.
6. **D01 date relabeling or naked equality deletion — NOT FOUND.** `DECISION_RESOLUTION_PLAYBOOK.md:5-16` requires actual emission receipts, explicit validity/revocation intervals, owner implementation, positive and negative cases, and expressly forbids date relabeling, naked equality-check removal, and invented PASS. `FIRST_WAVE_RUNBOOK.md:24-34` and master Packet A repeat those constraints.
7. **Invented B1 anchors / universal score / forced 15-session hold — NOT FOUND.** `FABLE_META_CEO_EXECUTION_HANDOFF.md:26` separates three sleeves, forbids a universal score and forced holding rule, and confines 2–15 sessions to tactical new-entry identity. `SUPERSESSION_MAP.md:13-17`, branch gate R6-A01/R6-A03, and `FIRST_WAVE_RUNBOOK.md:42-52,60-68` preserve board-row versus B1/canonical-episode distinctions and require owner acceptance for extra anchors.
8. **Five branch clarifications — each removes only a false global dependency; none weakens a real identity/availability/source/promotion gate.**
   - R6-A01 (`effective/ACTIVATION_GATES.json:120-132`): an existing board-pool view need not prove every row is a B1 episode, while current source/publication, board-row/canonical semantics, and PR custody remain.
   - R6-A02 (`:134-145`): optional specialist families may be visibly absent, while exact claimed identity/generation, source rights, and typed missingness remain.
   - R6-A03 (`:147-162`): original-grain board-row research need not wait on live B4, new anchors, or a publisher deployment, while valid keys, immutable source meaning, D03/D06/D07/D08, original protocols, episode/live-branch prerequisites remain.
   - R6-A04 (`:164-176`): research-to-watch may be honestly unavailable rather than promoted, while refusal projection, entitlement/readback, and research/control labeling remain.
   - R6-A05 (`:178-190`): offline model research need not wait for completed UI, while qualified data/evaluation, D06/D07, immutable identities, and separate live promotion gates remain.
9. **Verifier PASS as scientific/product proof — NOT FOUND.** See m1. The packet's scope labels and zero-test accounting keep integrity success separate from science and product acceptance.
10. **Acceptance entries — all NOT_EXECUTED.** `effective/ACCEPTANCE_CATALOG.json` has 126 cases, all `execution_status: NOT_EXECUTED`; `R6_HANDOFF_ACCEPTANCE.json` has 30 cases, all `status: NOT_EXECUTED`. No case was treated as passed by this review.
11. **Card/catalog contradictions — spot-check passed.** B05 and B07 work cards match `effective/BUILD_PROGRAM.json` dependencies, research packets, decision IDs, owners, technical owners, and external routing. Q01 and Q05 cards match `effective/RESEARCH_DOCKET.json` question, owner, consumers, external routing, and bounded Fable duty.
12. **Agent OS DEC record — schema and authority check passed.** Required `decision.schema.yml` fields are present and typed: key, question, answer, rationale, alternatives, evidence, affects, confidence, reversibility, decided_by, and decided_at. `decided_by: chairman` and `reversibility: easy` are present. The wording scopes authority to the full Prophet US build; preserves technical, custody, evidence, review, runtime, financial, and reserved human gates; invents no runtime role or provider; and explicitly disclaims automatic custody. It does not grant authority beyond the cited Chairman end-to-end delegation.

## CHECKS RUN

All commands ran from this exact local head. `rc` records the command's own exit status, not a surrounding pipeline.

1. `cd research/prophet_v4/r6_fable_meta_ceo_handoff && python3 verify_handoff.py | tail -30`
   - Tail: `HANDOFF VERIFICATION FAILED: [Errno 2] No such file or directory: '.../archives/R5_source_packet.zip'`
   - `rc=1` (confirmed without `tail`; the requested pipeline happened to print `rc=0` because the shell records `tail`.)
   - Follow-up byte reconciliation: 110 manifest entries; 108 present with exact size and SHA-256; missing `archives/R5_source_packet.zip` and packet-local canonical Agent OS record.
2. `python3 scripts/agentos.py validate 2>&1 | tail -2`
   - Tail: `::warning title=agentos-review-overdue::... review_by 2026-09-20 has passed` / `agentos: 1212 records (...) — 0 error(s), 90 warning(s)`
   - `rc=0`
3. `ls agentos/workstreams/ | grep -E "PROPHET-US|EARNINGS|GMI|FUSION|AVAILAB|ENTRY-TIMING"`
   - Found all six DEC `affects:` workstreams: `WS-EARNINGS-INTELLIGENCE-OS`, `WS-GMI-THEME-GRAPH`, `WS-PROPHET-CONDITIONAL-FUSION`, `WS-PROPHET-US-AVAILABILITY`, `WS-PROPHET-US-ENTRY-TIMING`, `WS-PROPHET-US-V4-RECOVERY`; `rc=0`.
4. Master-plan delta only: `diff baseline_r5/PROPHET_US_MASTER_PLAN_R5.md effective/PROPHET_US_MASTER_PLAN_R6.md | wc -l` = `124`; the required first-400 review covered the entire delta. Changed sections: title/metadata, carrier crosswalk paths, chapter 21 (“Astra, Fable, and external-fabric execution” → “Fable Meta-CEO and external-fabric execution”, with subsections 21.1–21.4), chapter 26 (“Immediate continuation and finalization boundary” → “Immediate execution and completion boundary”), and reference paths from packet-relative to `../baseline_r5/`. Unchanged R1–R5 science was not re-adjudicated.

## LIMITS

- This is a document/governance review, not a scientific audit, code review, runtime dispatch, model evaluation, production test, or source-custody adjudication.
- I did not re-read unchanged R1–R5 science, all 29 build cards, all 24 research cards, all 156 acceptance objects, every baseline member, issue #6805, the cited Mastermind blobs, current states of referenced PRs #7180/#7572/#7581/#7584/#7734/#7738/#7751, runtime/provider admission, credentials, checks, deployments, or live behavior.
- I did not verify the omitted zip digest because the file is absent. I verified the 108 present manifest entries, including the exact canonical Agent OS decision at its repository path.
- The shared Claude memory index named by repository startup law was unavailable at the supplied path, so I could not open the three delivery memories. This review does not merge or deploy and therefore does not depend on them.

## NEXT ACTION

Fable should repair B1 by the smallest exact-byte route above, rerun the packet verifier and Agent OS validation at the repaired head, obtain a separate independent review of any substantive packet/verifier repair that needs non-author independence, update the PR's local-proof truth, and only then adopt the R6 baseline and dispatch the first ready bounded unit through an actually admitted external route.
