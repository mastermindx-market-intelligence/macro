# B08 — Q06 Gate S acceptance readiness record (2026-10-21)

**CLASS:** C1 research (read-only except this file). **PROPOSED only — the program's Fable seat decides acceptance.**
**BASE:** `e5dd30c6344e4b62a0beba054ac4da97e00bab36` (branch `lane/pro-intel-b08gates-20261021-r1`, clean worktree).
**Subject:** `research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_source_contract.v0_2.json` (merged 2026-10-05, commit `24568cab0656`, PR #8069) — Gate S state and the records around it.
**Method:** every claim below is quoted or cited as `file:line` (JSON as file + key path). No outcome data was opened; no PR head was checked out (head reads were `git show <sha>:<path>` / `git cat-file -e <sha>^{commit}` only).

A premise-level finding up front, because it changes the question: **a BASE record already records a parent acceptance of this exact contract.** `research/prophet_v4/earnings_semantics_v1/README.md:81-84`:

> "Parent Sol independently reproduced the repaired Gate-S contract on current Macro PR #8069 head `ae9409bca5d81dbf7438ff0037a976b324853bdd` and accepted that **factual source field only** in #8069 comment `5894923827`."

I verified the contract file at BASE is byte-identical to that head: `sha256sum` of the BASE file = `a0790967ad56740fe740e7026e53eda34f3c2529ca75d6dfca64d28b293a177d`, and `git show ae9409bc:research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_source_contract.v0_2.json | sha256sum` returns the same digest. So the question is not only "can Gate S be accepted" but also "the contract's pending-state text is itself stale at BASE" (§7-D/E).

---

## 1. Verifier

Run from the repo root exactly as instructed:

```
python3 -I research/prophet_v4/r6_program/wave3/verify_q06_sec_comparable_revenue_source_contract.py; echo "exit=$?"
```

**Exit code: 0.** Full output (1 line, well under the 60-line cap):

```json
{"authority_all_false": true, "economic_id": "econ:50d783276670de14acd15a92317b93649d877c01f7d48961d1c56e5e7c87a656", "feature_value_pct": 16.356501765281383, "field_provenance_id": "fpv:36091b7aff3681e59ab527eb3ebeac61a20324195a9f43f4478c4ccbcff1566a", "gate_e": "NOT_REGISTERED_PREPARATORY_ONLY", "gate_s": "REPAIRED_PENDING_PARENT_ACCEPTANCE", "historical_envelope_identities": 10, "normalization_witness_normalized_sha256": "070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb", "normalization_witness_raw_sha256": "be6971e00004345bacedaccd598f89e76e7f6480707ecab88c64a5c4ae31d257", "schema": "prophet.q06.sec_comparable_revenue_source_contract.v0.2"}
```

No assertion failed. What the verifier proves at BASE (`verify_q06_sec_comparable_revenue_source_contract.py`): frozen fixture SHA-256 (`:19`, `:48`), rights-register git blob (`:20`, `:49`), economic-id re-derivation and exact arithmetic `(109417/94036-1)*100 = 16.356501765281383` (`:53-56`), field-provenance-id re-derivation (`:60-61`), span bytes `109,417`/`94,036` + text hashes + statement title + `Three Months Ended` (`:63-72`), the synthetic-envelope→wrapper-removal→frozen-body witness (`:74-88`), 10 distinct envelope identities with baseline/unexplained classifications and no issuer-revision claims (`:90-98`), Gate S/Gate E states, all-false downstream and authority (`:100-108`).

## 2. Gate S criteria

Contract `.gate_s` verbatim (`q06_sec_comparable_revenue_source_contract.v0_2.json:234-245`):

```json
"gate_s": {
  "state": "REPAIRED_PENDING_PARENT_ACCEPTANCE",
  "blockers": [],
  "review_findings": {
    "M1": "REPAIRED_BY_ENVELOPE_VS_NORMALIZED_BODY_SEPARATION",
    "M2": "REPAIRED_BY_SEPARATE_FIELD_PROVENANCE_IDENTITY",
    "M3": "REMOVED_FROM_GATE_S_AND_DOWNGRADED_TO_PREPARATORY_GATE_E",
    "m1": "REPAIRED_FIXTURE_CLOCK_CLASSIFIED_MALFORMED",
    "m2": "REPAIRED_EXACT_STATEMENT_TITLE_BOUND",
    "m3": "REPAIRED_BY_COMMITTED_VERIFIER"
  }
}
```

Gate S's substantive criteria are defined in the repair doc §3, `Q06_SEC_COMPARABLE_REVENUE_SOURCE_METHOD_REPAIR_2026-09-29.md:93`: "It requires source identity, rights, clocks, fiscal comparability, spans, normalization and correction/provenance semantics. It does **not** need a matured trading result." Recorded state of each:

| Criterion | Recorded state in contract | Supporting location in repair doc |
|---|---|---|
| Source identity | `.field_provenance.source_document` pins object id `sec:0000320193:0000320193-26-000018:EX-99.1`, CIK, accession, form 8-K, exhibit, URL, frozen+normalized hashes (`:53-63`) | §2 `:70` "exact SEC document identity / CIK / accession / form / Exhibit 99.1" bound in the fpv identity |
| Rights | `.field_provenance.rights` = path `research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md`, blob `a9ee6f28…`, state `ALLOWED_WITH_RECORDED_LIMITS` (`:83-87`) | §2 `:79` "the pinned source-rights record path, blob and allowed-with-limits state" |
| Clocks | `.field_provenance.clocks.source_available_at = 2026-07-30T20:30:28Z`; fixture clock "malformed timezone/truncation metadata and is not decision authority" (`:92-95`) | §4 m1 `:119` "malformed timezone/truncation fixture metadata … Source authority remains `2026-07-30T20:30:28Z`" |
| Fiscal comparability | `.table` title "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)", column_role "Three Months Ended", GAAP mapped by contract not manifest token (`:64-68`); current/prior periods `:34-47` | §2 `:73-76` (title + column role bound); §4 m2 `:121` |
| Spans | `.current_span` [19519,19526) and `.prior_span` [20003,20009) in normalized body bytes, both with text SHA-256 (`:69-82`) | §2 `:75-76` "both UTF-8 byte spans and text hashes"; §1 table `:45-46` (positions 19,519 / 20,003 re-reproduced 2026-09-29) |
| Normalization | `.normalization` rule `sec_suffix_delivery_script_v1`, scoped to this one exhibit, with byte-exact recheck witness and `UNEXPLAINED_ENVELOPE_CHANGE` policy (`:97-121`) | §1 `:16-52` (frozen rule text `:18-35`; reproduction table `:39-47`; fail-closed classification `:52`) |
| Correction/provenance semantics | `.correction_semantics` (`:228-233`) + `.historical_envelope_identities` — 10 identities, baseline + 9 `UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY`, all `issuer_body_revision_claim: false` (`:122-227`) | §1 `:12-14` (v0.1 "source-body revisions" wording withdrawn), `:52`; §2 `:81` (provenance change cannot stay "the same field") |

Finding closure: the six review findings map to repairs at contract `:237-244`, evidenced by repair doc §1 (`:10-52`, M1), §2 (`:54-81`, M2), §3 (`:83-115`, M3), §4 (`:117-125`, m1–m3). `blockers: []` (`:236`).

## 3. Prior findings against v0.1

All six defects were raised by the independent GLM-5.3 review `reviews/Q06_SEC_COMPARABLE_REVENUE_SOURCE_METHOD_REVIEW_GLM53_2026-09-27.md` (DISPOSITION `FIX_REQUIRED`, `:17`) and are echoed in the repair doc. The manifest and receipt are themselves v0.1 artifacts (no defect list against v0.1); the capture doc self-records limits. Git history: every Q06 path (contract, manifest, receipt, repair doc, capture doc) has exactly one commit at BASE — `24568cab0656 2026-10-05 research(prophet): Q06 SEC comparable-revenue source contract (#8069)`.

| Finding | Where raised | Where v0.2 answers it |
|---|---|---|
| **M1** — ten distinct full-string hashes "do not prove ten issuer-authored exhibit-body revisions"; daily changes consistent with mutable delivery wrappers | review `:29-33` (effect: `candidate.md:97-99`, `:105`, `receipt.json:13-21`) | contract `.normalization` `:97-121` + `.historical_envelope_identities` `:122-227` (all rows `issuer_body_revision_claim: false`); repair doc §1 `:10-52` |
| **M2** — field provenance versioning omits source-object identity, spans, admissibility, rights | review `:35-39` (effect: `candidate.md:118-123`) | contract `.field_provenance` `:51-96` + `.correction_semantics` `:228-233`; repair doc §2 `:54-81` |
| **M3** — v0.1 "preparatory, not genuinely preregisterable"; post-outcome degrees of freedom | review `:41-45` (effect: `candidate.md:164-227`) | contract `.gate_e` `NOT_REGISTERED_PREPARATORY_ONLY` + 11 `required_before_registration` items `:246-264`; repair doc §3 `:83-115` ("first preregisterable construction" phrase superseded, `:85-87`) |
| **m1** — malformed fixture clock underdiagnosed | review `:49` (`candidate.md:50-51`) | contract `.clocks.fixture_clock_disposition` `:93-95`; repair doc `:119` |
| **m2** — GAAP label lacks exact source title | review `:51` (`candidate.md:62-63`) | contract `.table` `:64-68`; repair doc `:121` |
| **m3** — validation command named an uncommitted temp script | review `:53` | committed verifier `verify_q06_sec_comparable_revenue_source_contract.py` (runs green, §1) + `tests/test_q06_sec_comparable_revenue_source_contract.py` (present at BASE); repair doc `:123-125` |
| Self-raised: D07 SEC comparable-event row null; register "still Draft/unmerged on #7856"; cohort not confirmatory | capture doc `:154-157` | Partially: v0.2 keeps replay diagnostic-only and confirmatory evidence prospective (repair doc `:113`); the event-set reconstruction itself is **not answered** — it remains the D07 register row `S2-sec-comparable-events` (null `EVENT_SET_NOT_RECONSTRUCTABLE`, blocks B08; `D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md:62`, adoption ruling `:37`) |
| Self-raised: field not materialized in current D5 (`no_span_addressable_evidence`) | capture doc `:71-75` | repair doc §5 `:129-140` (post-Gate-S job = extend existing owner-native path); see §6/§7 — at BASE a consumer exists |

## 4. D07 evidence class

**Register location.** `git log --format='%h %s' --grep='7856'` → `509ffb5a6a5c R6-D07-01: adopt the evidence-class register v1 (#7856)` (merged 2026-09-27). `git show --stat` names four files: `reviews/RV_7856_D07_REGISTER_OPUS_2026-09-24.md`, `rulings/R6-D07-01_EVIDENCE_CLASS_REGISTER_ADOPTION_2026-09-27.md`, `wave3/D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md`, `wave3/d07_evidence_class_register_draft.json`. The draft md carries `STATUS: ADOPTED as register v1 by R6-D07-01 (2026-09-27)` (`:3`).

**Class definitions** (`D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md:11-14`, identical in `d07_evidence_class_register_draft.json` key `classing_rule`):

> - **OBSERVED_AS_RUN**: input identity, release clock, observed clock (a capture receipt stamped by the writer at write time) and correction clock all recorded at capture; any model in the path pinned at decision time; store generation pinned.
> - **PUBLIC_INFO_REPLAY**: source-recorded release and correction (vintage-boundary) clocks exist for every input row used; no model of unknown vintage in the path; no capture clock required.
> - **RETROSPECTIVE**: a KNOWN, identifiable construction (code blob, selection era, unfitted-but-selected head, or a model of unknown vintage) whose knowledge boundary cannot be proven not to include the future of the decisions it would be applied to. The label names a known construction with an unprovable boundary.
> - **null**: a required element is ABSENT or UNIDENTIFIED … nothing to class yet; the consumer is blocked pending the prospective remedy.

**Rule that assigns a class** (adoption ruling `R6-D07-01…md:22-25`, binding):

> "1. A class may be raised only by a receipt satisfying the classing rule at a named SOURCE_SHA; never by assertion, never by a consumer. `OBSERVED_AS_RUN` requires a writer-stamped capture clock and a pinned store generation (F1).
> 2. A known construction with an unprovable knowledge boundary is `RETROSPECTIVE`; an absent or unidentified element is `null` (F3). A model of unknown vintage in the path caps the row at `RETROSPECTIVE` (F2)."

Register changes move md+json together in a new PR citing R6-D07-01 (`:30-31`).

**PROPOSED class for the AAPL FY2026 Q3 exemplar: `PUBLIC_INFO_REPLAY`.** Applying the quoted rule to the v0.2 contract:

- The single input row used is the frozen normalized exhibit body (`fpv` pins body hash `070abd6a…`, contract `:60-61`); its release clock is source-recorded — SEC acceptance `2026-07-30T20:30:28Z` (contract `:93`; independently reproduced in review challenge C, review `:73`). No SEC amendment or successor vintage exists for accession `0000320193-26-000018` in any Q06 record, and envelope variability is quarantined (`UNEXPLAINED_ENVELOPE_CHANGE`, contract `:120`), so no correction boundary is left unbounded.
- No model of unknown vintage is in the path: construction is the deterministic rule `sec_suffix_delivery_script_v1` + fixed arithmetic, and all seven authority flags are false (contract `:9-17`, `:100`).
- "No capture clock required" is explicit in the class definition — which matters because `captured_at` is not asserted anywhere in this pipeline (the register's own S1 cells: "captured_at is explicitly not asserted", draft md `:47`), so `OBSERVED_AS_RUN` is unavailable under ruling §3.1.
- Not `RETROSPECTIVE`: the construction is known and pinned and its knowledge boundary is the source-recorded release clock, not an unprovable future. Contrast `S5-d5-earnings-context` (`RETROSPECTIVE`, draft md `:71`), whose remedy — "freeze the source body, extraction model and prompt version, output hash, all clocks, and generation identity" — is precisely what contract v0.2 supplies for this exemplar.
- This matches the capture record's own proposal (`proposed_diagnostic_class: PUBLIC_INFO_REPLAY`, manifest `:102`) and the capture doc's "public-information replay is diagnostic only" (`:160`).

Caveats: (a) the class is **not registered** — the register's 31 rows contain no AAPL/Q06 exemplar row (grep of the JSON for `aapl|q06|apple` = 0 hits), so manifest `.evidence_class.registered_value: null` is accurate; raising the class requires a new register row per ruling `:30-31`. (b) The B08 consumer disposition stays `BLOCKED pending the SEC event-set reconstruction and source-release routes, plus a frozen prospective model` (ruling `:37`) — the exemplar's class does not unblock the B08 event-set row.

**Manifest `.evidence_class` verbatim** (`q06_sec_comparable_revenue_capture_manifest.v0_1.json:99-104`):

```json
"evidence_class": {
  "registered_value": null,
  "basis": "D07_OPEN_PR_7856_UNMERGED",
  "proposed_diagnostic_class": "PUBLIC_INFO_REPLAY",
  "confirmatory_path": "PROSPECTIVE_ONLY"
}
```

## 5. Rights pin

- History: `git log --format='%h %ad %s' --date=short -- research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md` → exactly one commit: `2d688de23107 2026-09-24 research(licenses): Prophet US source rights register (R6-D03-01 §4; records only) (#7843)`. The register has never changed since creation.
- `git hash-object` at BASE: `a9ee6f288bfb2716facd88dcf2c5135ca8125303` — **equals the pin** (contract `.field_provenance.rights.blob`, `:85`; verifier `EXPECTED_RIGHTS_BLOB`, `:20`, asserted at `:49` and green in §1).

SEC EDGAR rights row — summary row (`…REGISTER_2026-09-23.md:225`):

> `| SEC EDGAR | User-facing with citation and trademark limits | A filing-specific third-party restriction. |`

Full family determination (`:113-121`), all five dimensions `DETERMINED-FROM-PUBLISHED-TERMS` from `sec.gov/privacy.htm#dissemination` fetched 2026-09-23T19:37:19Z ("considered public information"; "may be copied or further distributed… without the SEC's permission"), postures **user-facing**, redistribution "user-facing, citation-and-trademark-limited" (`:121`). The single missing answer that could change the posture: "A filing-specific third-party restriction." (`:225`).

## 6. Downstream

Contract `.downstream` verbatim (`:265-270`): `d5_adapter_edit_authorized: false`, `packet3_trial_authorized: false`, `rank_change_authorized: false`, `user_entry_authorized: false`.

Contract `.gate_e` verbatim (`:246-264`): `state: NOT_REGISTERED_PREPARATORY_ONLY`, `protected_outcome_read: false`, `numerical_result: UNCOMPUTED`, `trial_may_start: false`, and `required_before_registration` = eleven items (`:251-263`) from "exact directional estimand" through "accepted Data OS outcome-price basis".

**What must be true before the incumbent Earnings/D5 owner may materialize the field** (per the contract's own text):

1. Gate S parent acceptance — `.next_action` (`:271`): "Parent reviews Gate S v0.2. If accepted, incumbent Earnings/D5 owner may materialize the exact factual comparable-revenue field under its existing contract". Repair doc `:158`: "Gate S parent acceptance is the next decision. After that acceptance, the existing Earnings/D5 owner may implement the factual field."
2. Materialization stays inside the incumbent owner's existing contract/adapter (repair doc §5 `:136-138`: "extend the existing owner-native Earnings event/workspace → existing D5 family path … while retaining correction-safe PIT reads and all-false rank/entry authority"; the pre-existing shell is `engine/prophet_lab/intelligence_vector.py::build_earnings_intelligence_vector`, `:131`).
3. The consumer's own pins (as built, `D5_CONSUMER_2026-09-30.md:34-40`): production reads the one canonical #8069 source-contract path, contract SHA-256 must equal `a0790967…`, rights blob must retain `a9ee6f28…`, plus same issuer/event, exact D5-selected normalized source hash, matching source clock, admissibility, identical normalized current revenue value.
4. Gate E completed by Evaluation **before any outcome access** (contract `:271`; `.gate_e.required_before_registration` `:251-263`).

**Where the field lands** (cited lines only, no code): an authenticated detail endpoint `GET /api/prophet/lab/v1/episodes/{episode_id}/earnings` invokes the existing B1/D5 episode-intelligence function and projects through `engine/prophet_lab/earnings_dossier.py`; the detail "shows reported revenue and, where the exact qualified Q06 companion matches, current/prior values, comparable quarterly growth, economic identity and field provenance" with all financial authority false (`D5_CONSUMER_2026-09-30.md:14-31`). The pure evidence functions live in the existing `engine/sue.py` owner and "preserve source-contract references and stamp all financial authority false" (`earnings_semantics_v1/README.md:97-111`); the R3 section points to the D5 consumer doc for "its exact Q06 dependency, 196-test combined proof … and remaining UI/release work" (`README.md:140-146`). Output is labeled `RETROSPECTIVE_FACTUAL_RECONSTRUCTION_NO_AS_RUN_PROMOTION`, `is_original_as_run_recommendation=false` (`D5_CONSUMER…:62-68`). At BASE this code exists (added by `f0e501324a5f 2026-10-05`, which also added the `earnings_semantics_v1/` docs); the doc itself states "**BUILT_NOT_PROVEN / MISSION_COMPLETE:false. Source candidate, not deployed.**" (`:3`) and that release, CI and UI wiring remain open (`:54-55`, `:110-131`).

## 7. Stale records (text vs facts at BASE)

Checked with `git log --oneline --grep='#<n>'` where a PR state is claimed. Quotes: left = record text, right = BASE fact.

- **A. Manifest `.evidence_class.basis`** (`q06_sec_comparable_revenue_capture_manifest.v0_1.json:101`): `"basis": "D07_OPEN_PR_7856_UNMERGED"` — vs `509ffb5a6a5c R6-D07-01: adopt the evidence-class register v1 (#7856)` merged 2026-09-27, and draft md `:3` "STATUS: ADOPTED as register v1 by R6-D07-01 (2026-09-27)". Note the manifest itself merged 2026-10-05 in `24568cab0656` — the basis was already stale at merge time.
- **B. Capture doc** (`Q06_SEC_COMPARABLE_REVENUE_PROSPECTIVE_CAPTURE_2026-09-26.md:156`): "the D07 register itself is still Draft/unmerged on #7856" — vs the same merged commit. (Historical doc; repair doc `:168` keeps v0.1 immutable, so this is superseded text, not a live claim.)
- **C. Manifest `.next_action`** (`:134`): "independent source-method review; on acceptance Packet3 registers one prospective trial" — vs review completed 2026-09-27 (`FIX_REQUIRED`), repair v0.2 dated 2026-09-29, and the acceptance recorded in README `:81-84`. Also superseded in shape: v0.2 routes any trial behind Gate E (contract `:246-264`), not straight from acceptance.
- **D. Contract `.state`** (`:8`) and `.gate_s.state` (`:235`): `"GATE_S_REPAIRED_PENDING_PARENT_ACCEPTANCE"` / `"REPAIRED_PENDING_PARENT_ACCEPTANCE"` — vs README `:81-84`: Parent Sol "accepted that **factual source field only** in #8069 comment `5894923827`" on head `ae9409bc`, whose contract bytes are byte-identical to BASE (digest `a0790967…`, §header). The state field was never updated after that acceptance. (The comment itself is not offline-verifiable — see GAPS.)
- **E. Contract `.next_action`** (`:271`): "Parent reviews Gate S v0.2. If accepted, incumbent Earnings/D5 owner **may** materialize…" — vs the same acceptance record, plus the materialization already built at BASE (§6: endpoint + dossier + 196-test proof, BUILT_NOT_PROVEN).
- **F. Contract `.downstream.d5_adapter_edit_authorized: false`** (`:266`) and manifest `.feature.materialized_by_current_d5: false` / `"current_d5_state": "current revenue present; prior comparable typed absent"` (`:55-56`): as grants/observations of the 2026-09-26 world. At BASE the D5 detail consumer projects the comparable prior and growth (D5_CONSUMER `:26-31`), and repair doc §5 `:134` "it does **not** currently materialize this same-table comparable prior" is likewise outdated. The authority flags remain true as *grants* (nothing in these records authorizes anything); the stale part is the descriptive present-tense.
- **G. Superseded "source-body revisions" terminology**: receipt keys `.distinct_source_revision_count: 10` (`q06_aapl_revision_chain_receipt.v1.json:13`) and `.revisions_oldest_first` (`:21`); manifest `.production_chain.distinct_source_revisions: 10` (`:80`); capture doc "10 distinct source-body revisions" (`:99`, also `:108`). Contract `.supersedes[1]` (`:5-6`): "prophet.q06.aapl_revision_chain_receipt.v1 terminology that called distinct supplied envelope hashes source-body revisions"; v0.2 classifies them `UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY` (`:143` etc.).
- **H. Capture doc `:17`**: "The first preregisterable Q06 construction" — vs repair doc `:85-87`: "The phrase **'first preregisterable construction'** in v0.1 is superseded."
- **I. Capture doc `:51`**: fixture clock "conflicts with production; not used as the decision clock" — vs contract `:94` "malformed timezone/truncation metadata … not decision authority" (m1 upgrade from "conflict" to "malformed").
- **J. Capture doc §5 arms/experiment sketch (`:164-227`)** framed as preregistration candidate — vs M3 downgrade to research questions (repair doc `:113`).
- **Checked and NOT stale:** manifest `.held.cycle_pr_7868` / `cycle_pr_7871` (`:129-130`) — no merge commit at BASE references #7868 or #7871, so "held" stands uncontradicted (offline git cannot distinguish open vs closed-unmerged). Manifest `.experiment.evaluation_owner` "Packet3 / #7288" (`:120`) — no #7288 merge commit at BASE; not contradicted. Manifest `.evidence_class.registered_value: null` — accurate; the adopted register has no exemplar row (§4).
- **Explained discrepancy (not staleness):** contract `.source_review.review_head = a3bee6f…` (`:20`) vs review doc "REVIEW TARGET HEAD: `1b063d3a…`" (`:6`). Both objects exist on host: `1b063d3a` = "docs(agentos): bind Prophet Q06 outcome price gate" (2026-09-26 20:53), `a3bee6f` = "docs(prophet): independently review Q06 source method" (2026-09-26 22:07) — i.e. the head the review targeted vs the head that carries the completed review record.

## 8. PROPOSED verdict

**PROPOSED: ACCEPT** — Gate S acceptance of the Q06 SEC comparable-revenue source contract v0.2, factual source field only (matching the already-recorded acceptance scope), with the record edits below. Reasons (each points at a section above):

1. The committed verifier is green at BASE from a clean worktree — fixture, rights blob, both identities, spans, arithmetic, normalization witness and envelope classifications all reproduce (§1).
2. All three majors and three minors from the independent review are repaired with committed, quotable evidence; `blockers` is empty (§2, §3).
3. The rights pin is exact: sole-commit register history, BASE blob equals the pin, SEC EDGAR user-facing with citation/trademark limits (§5).
4. A parent acceptance of these exact bytes is already recorded at BASE (README `:81-84`, comment `5894923827`, head `ae9409bc`; byte-identity verified) — a fresh ACCEPT ratifies the artifact the program already acted on, rather than opening a new one (§7-D).
5. Gate E is correctly walled off — `NOT_REGISTERED_PREPARATORY_ONLY`, no outcome read, no trial; acceptance of Gate S leaks no outcome authority (§6).
6. The D07 gap is a missing register row, not a source-method defect: PROPOSED class `PUBLIC_INFO_REPLAY` with a lawful raising path (new row, PR citing R6-D07-01); B08's event-set blockage is separate and untouched (§4).
7. Every stale item found is companion-record hygiene (manifest basis/next_action, contract state fields, superseded v0.1 terminology); none touches the pinned identities, hashes or evidence (§7).
8. The downstream consumer pins this exact contract SHA and rights blob (§6), so ACCEPT creates no fork between the accepted record and the implemented dependency.

**Proposed record edits (path + key/line + new text — proposed only, none applied):**

1. `research/prophet_v4/r6_program/wave3/q06_sec_comparable_revenue_capture_manifest.v0_1.json` `.evidence_class.basis` → `"D07_REGISTER_V1_ADOPTED_R6-D07-01_2026-09-27_509ffb5a6a5c"`.
2. Same file `.next_action` → `"Gate S accepted (factual source field only; see earnings_semantics_v1 README and this readiness record). Gate E owned by Evaluation and required before any outcome access."`
3. Same file `.feature.materialized_by_current_d5` / `.current_d5_state` → `true` / `"comparable field projected by authenticated D5 earnings detail (BUILT_NOT_PROVEN, not deployed)"` — or annotate the block superseded-by.
4. Do **not** byte-edit the contract's `.state`/`.gate_s.state`/`.next_action` in place: the D5 consumer pins the contract file SHA-256 `a0790967…` (D5_CONSUMER `:34-37`) and the verifier asserts `gate_s.state == "REPAIRED_PENDING_PARENT_ACCEPTANCE"` (`verify…py:100`), so any in-place edit breaks both pins. Prefer a separate acceptance/ruling record; if the seat elects an in-place state change anyway, the same change must update the consumer pin and the verifier/test expectations together.
5. If the class is to be carried on consumers: add an exemplar row (PROPOSED `PUBLIC_INFO_REPLAY`) to `wave3/D07_EVIDENCE_CLASS_REGISTER_DRAFT_2026-09-24.md` + `d07_evidence_class_register_draft.json` in one PR citing R6-D07-01, then set manifest `.evidence_class.registered_value`.
6. Leave the capture doc, receipt and repair doc as immutable historical evidence per repair doc `:168`; this readiness record is their cross-reference.

---

**Outcome files avoided:** none had to be abandoned — no file under `data/prophet/ledger*`, `*scoreboard*`, `*track_record*`, `*outcome*` or `*returns*` was opened. The Massive price-manifest facts above are quoted from the Q06 records, not from `data/`.

**GAPS:** (1) PR #8069 comment `5894923827` (the recorded parent acceptance) is not offline-verifiable; it is reported as quoted bytes from `earnings_semantics_v1/README.md:81-84` at BASE. (2) Open/closed state of #7868, #7871, #7288, #8189 is unresolvable without network; only absence of merge commits at BASE is established. (3) The nine non-baseline envelope raw bytes are not on host (repair doc `:52`), so their normalization is unverifiable — recorded as `UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY`, no attempt made. (4) No merge commit at BASE carries the string `#8189`; the earnings-semantics docs and `engine/prophet_lab/earnings_dossier.py` are at BASE via `f0e501324a5f` (2026-10-05), whose subject carries no PR reference.

**DEVIATIONS:** none. Verifier run verbatim from the repo root; PR-head reads were `git show`/`git cat-file -e` only; single report file written; no push, PR, label or merge.
