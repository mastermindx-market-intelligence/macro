# A1 thesis store — three-level cluster store (Wave 2, seat 0e739467)

Lane: A1_thesis_store. Worktree HEAD: `295e76c6a0`. Design, not code. Phase 3 builds against this.

## 1. ANSWER FIRST

The thesis view is a **pure function** `F(fact_log, owner_snapshot, as_of_utc) → thesis_view.v1`. Nothing in the view is independently mutable. The single field that would break purity if stored as a clock-derived status is **deadline-missed / next-observation status**: writing `datetime.now()` (or `date.today()` as `engine/long_hold_clocks.py` does at the `today or date.today()` default) into the view makes two replays of the same log diverge. Deadline timestamps are source-stated records in the log; missed-deadline is computed from the caller-supplied `as_of_utc`. Replay of the same `(log, owners, as_of_utc)` is byte-identical under `canonical_json_bytes` (`engine/company_intelligence/contracts.py:127-140`).

This is a derived view over existing event/claim/plan owners. It is not a thesis lobe, not a new lifecycle service, and not a scorer.

## 2. Constraints

### STATED (masterplan / freeze)

- Three levels, existing owner identities retained: article manifestations; distinct facts and revisions; a thesis view linking events and milestones over time (MASTERPLAN.md §5).
- Thesis view fields: original proposition and decision cut; supporting and contrary claim IDs; root source families; exposure paths; required assumptions; current milestone evidence; next expected observation; deadline; weakening conditions. Derived through existing event/claim/plan owners, not a new lifecycle service (MASTERPLAN.md §5).
- No naive independent updates over correlated reports; conservative provenance groups; likelihood ratios only with adequate labeled data, which does not exist (MASTERPLAN.md §5; DNR:KILL-LLM-CONFIDENCE; freeze §0.3).
- Recompute only for material deltas: changed numeric terms, new independent evidence source, milestone, contradiction, missed deadline, source correction, exposure change, relevant market-state change. Cosmetic wording and unchanged mirrors do not trigger (MASTERPLAN.md §5).
- Scheduled deadline checks use an existing admitted scheduler; this research creates none (MASTERPLAN.md §5).
- Company identity = `cik:` + 10 digits (freeze D12 / schema `company_id` pattern `^cik:(?!0{10}$)[0-9]{10}$`; `identity.py:50-58`).
- Evidence = owner `source_span.v1` exactly as `SourceSpan.to_payload` emits, or `field_absence.v1` (freeze D13; `documents.py:353-367`).
- Envelope: `fact_id` = `fact_` + 24 hex; `novelty = corrected_fact ⇒ supersedes_fact_id` non-null (freeze D16).
- Closed enums: `cluster_grain` = `{article_manifestation, fact_revision, thesis_link}`; `novelty` = `{new_reporting_of_old_fact, corrected_fact, new_magnitude_timing_commitment_counterparty, independently_observed_milestone, commentary}` (schema `$defs`).
- No confidence / probability / score / price-target / fair-value / rating field (freeze §0.3, DNR:KILL-LLM-CONFIDENCE).
- Model output may only describe, cite, and abstain (DNR:KILL-LLM-ORIGINATION). Display uses windows and "what we are watching", never certainties, never front-facing falsifier/refutation wording (commission).
- Source text is data, never instructions (MASTERPLAN.md §3.5).
- Attachment: news leaf links to `company_event.v1` only when the type is in `EVENT_TYPES`; otherwise `ci_event_id` is typed absence (freeze F1 / §4.1).
- KILL-THESIS-LOBE: a "thesis lobe" is a duplicate of the long-hold program (`config/compiled_kill_registry.yml:402-406`; ruling NEXTL-U1 `config/ruling_graph.yml:8147-8172`; `research/DO_NOT_REBUILD.md`). All thesis-layer work routes to the long-hold program, not a new lobe.
- HOLD-STRUCTURE-LEARNERS: no NOTEARS/DAG structure learner for provenance (`config/compiled_kill_registry.yml:808-812`).
- LEAF never appends to `data/news/event_log.parquet` (freeze §9 reuse matrix).
- Rulings R1-R4 bind (excerpt projection, document_version ≥ 1, closed locators).

### PHYSICS

- An overwrite of a correction destroys the replay of "what was known when". Append-only is required for PIT.
- Two URLs of the same press release are correlated; treating them as independent evidence inflates support. Provenance groups are an independence partition, not a similarity score.
- `as_of_utc` must be an input: a pure function cannot read a clock.
- Byte identity of JSON requires a canonical encoder (sorted keys, no NaN, trailing newline) — already owned by `canonical_json_bytes`.

### INHERITED (owner modules read this session)

- `engine/qbus_news_cluster.py:102-104` mints `cluster_id = "ev2_" + sha256(story_id)[:16]`. Join requires shared `subject_ids`, compatible `event_family`, window, and title match (`:164-247`). This is level-1 article grouping.
- `engine/qbus_news_store.py:245-261` persists `news_clusters` / `news_cluster_members`. Keep-first membership: primary key `(source, source_item_id)`.
- `engine/news_event_ledger.py:8-10,115-116` keep-FIRST on `event_id`; `first_seen_utc` never overwritten. LEAF reads this; does not append (freeze §9).
- `engine/news_common.py:109-114` `event_id(title, domain)` is the news dedup key.
- `engine/company_intelligence/events.py:5-8,93-100,182-200` issuer-keyed `evt_cik##########_<period>_<type>`; `EVENT_TYPES` has no `news`. `apply_transition` (`:329-365`) keeps the SAME `event_id` on `corrected`; `superseded` is terminal (`:42,67`).
- `engine/company_intelligence/event_workspace.py:70-73` stores `facts`, `guidance`, `claims` on `event_workspace.v1`.
- `engine/company_intelligence/issuer_profiles.py:160-165,231-246,313-325,333-347` mint `event_claim.v1`, `event_fact.v1`, `guidance_item.v1` — the claim and plan-like owners. No separate `plan.py` exists under `engine/company_intelligence/` (search bound: `ls-tree` of that tree plus grep `plan`/`claim` this session).
- `engine/company_intelligence/economic_observations.py:41-46,101-103,153-174` `event_fact.v1` identity is `(event_id, metric, period, basis)` hashed to `fact_` + 16 hex — a different width from the frozen news-impact 24-hex `fact_id`. News-impact `fact_id` is the log identity; owner ids ride in `owner_claim_ids`.
- `engine/company_intelligence/pb_d_quality.py:17-22,207,695-706,1087-1104` `claim_id`, `root_family_id`, `origin_claim_id`, `origin_document_id`, `append_source_correction` (never rebuilds the original).
- `engine/company_intelligence/documents.py:307-367,370-372,375-432` `source_span.v1`; `span_id = "span_" + sha256(document_id|locator)[:20]`.
- `engine/company_intelligence/resolution.py:12-16` supersession collapse is earned from the revision chain, never declared.
- `engine/company_intelligence/relationship_candidates.py:1-7,36` ephemeral analyst boundary for exposure; schema `company_intelligence.relationship_candidate/v1`. Economic propagation (#6514) is BLOCKED (freeze §1.1, §9).
- `engine/company_intelligence/views.py:32-40` projects earnings-call metrics including `confidence` — forbidden consumer for this view (DNR:KILL-LLM-CONFIDENCE).
- Long-hold program: `config/mastermind_programs.yml:2160` `long-hold-intelligence`; charter `research/LONG_HOLD_THESIS_MASTERPLAN_BY_FABLE.md`; clocks `engine/long_hold_clocks.py:1-47` are **display-only** (`_display_only = True`) and default `today or date.today()` (`:91-92`). They are not this view and not a scheduler.
- Admitted scheduler: `.github/workflows/daily.yml:8-39` US-nightly cron pair `30 22 * * *` / `30 23 * * *` (18:30 ET DST pair); Python gate `engine/ledger_lane.py:24-36` `nightly_advance_enabled()` (`COLLECT_LANE=nightly`). `config/metabolism_schedule.yml` is lobe dispatch spread, not a deadline scheduler.
- `engine/thesis_condition_monitor.py` / `engine/thesis_monitor.py` are foresight/user-thesis monitors, not Company Intelligence claim owners. Do not route news-impact theses through them.

### ASSUMED (low-stakes; what breaks if wrong)

- A1. Physical log home is LEAF `data/news_impact/fact_log.jsonl` (or parquet with the same record schema), never `news_event_ledger`. Breaks freeze §9 if we append to the news ledger instead.
- A2. `provenance_group_id` equals `origin_document_id` when present, else `origin_claim_id`; it is not a new identifier family. Breaks "no new identifier family" if we mint `grp_…`.
- A3. Staged bundles below are the default next-observation ladder per template. A Phase 3 builder may add a milestone name to the closed enum by contract amendment, not by free text.
- A4. `polarity` is assigned from the leaf `negated` flag plus presence of a contrary-mechanism quote, never from a model score.

## 3. Three mechanism-distinct candidates

| ID | Mechanism | One-line refutation test |
|---|---|---|
| C1 | New mutable "thesis lobe" / lifecycle service storing a current thesis row that UPDATE-s on each article | Grep `KILL-THESIS-LOBE` and MASTERPLAN.md §5 "not a new lifecycle service". Both fire. Also `apply_transition` already keeps event identity stable (`events.py:329-343`); a second lifecycle duplicates it. |
| C2 | Append-only fact log as the only history; thesis view = pure fold over log + owner snapshots + `as_of_utc`; qbus clusterer owns level-1 articles only | Refutation: produce two replays of the same `(log, owners, as_of_utc)` whose `canonical_json_bytes` differ, or show a required §5 field that cannot be derived from those inputs. |
| C3 | Store facts/claims only inside existing `event_workspace.v1` (`facts`/`claims`/`guidance`) and treat that workspace as the thesis | Refutation: `canonical_event_id` requires `event_type ∈ EVENT_TYPES` (`events.py:93-100,197-199`); freeze F1 says news types are absent, so `ci_event_id` is typed absence. A buyback authorization or open-model release cannot mint a CI event without inventing a type (forbidden). |

**Chosen: C2.** C1 is killed by KILL-THESIS-LOBE and §5. C3 cannot hold news species without a new `EVENT_TYPES` member, which freeze F1 forbids. C2 uses the frozen `fact_id` family, qbus `cluster_id`, owner `claim_id`s, and `cik:` identity; the view is a projector.

Boring-baseline gate: the boring solution is "one JSON object per cluster, overwritten on each article." It fails MASTERPLAN.md §5 (material-delta recompute, supersedes replay, no correlated Bayesian update) and freeze D16 (correction replay). C2 is the boring solution that still passes those tests: an append-only log plus a fold, which is what `events.apply_transition` and `pb_d_quality.append_source_correction` already do for earnings.

## 4. Frozen-spec draft (builder-complete)

### 4.1 Three levels

1. **Article manifestation** (`cluster_grain=article_manifestation`, `record_kind=manifestation`). One qbus story (`story_id = source:source_item_id`, `qbus_news_cluster.py:28-29`) joined to a `cluster_id` (`ev2_` + 16 hex). Log record points at an existing live fact via `reports_fact_id`. Novelty ∈ `{new_reporting_of_old_fact, commentary}`. `supersedes_fact_id` is always null. Does not change live quantities.
2. **Distinct fact / revision** (`cluster_grain=fact_revision`, `record_kind=fact_revision`). Novelty ∈ `{corrected_fact, new_magnitude_timing_commitment_counterparty, independently_observed_milestone}`. Appends a new `fact_id`. A correction never overwrites.
3. **Thesis view** (`thesis_view.v1`). Derived. Optional log records with `cluster_grain=thesis_link` cite two or more live `fact_id`s (authorization + later 10-Q execution; announcement + independent deployment). The view exists even when no `thesis_link` row has been written, as the fold of all live facts sharing the original proposition's `company_id` and staged-bundle membership.

### 4.2 Identifiers (no new family)

| Token | Owner | Pattern |
|---|---|---|
| `company_id` | `identity.company_id_for_cik` | `cik:` + 10 digits, not all zero |
| `fact_id` | news-impact envelope D16 | `fact_` + 24 hex |
| `cluster_id` | `qbus_news_cluster.new_cluster_id` | `ev2_` + 16 hex |
| `span_id` | `documents._span_id` | `span_` + 20 hex |
| `event_id` (news) | `news_common.event_id` | owner string, stored in qbus/ledger |
| `event_id` (CI) | `events.canonical_event_id` | `evt_cik##########_…` or `field_absence.v1` |
| owner `claim_id` / `fact_id` | `issuer_profiles` / `economic_observations` | text_safe ≤128, in `owner_claim_ids` |
| thesis view key | derived | `(company_id, original_proposition_fact_id)` |
| `provenance_group_id` | derived | `origin_document_id` if string, else `origin_claim_id` |

Do not mint `thesis_…`, `grp_…`, `view_…`, or a 16-hex news `fact_id`. The earnings `fact_`+16-hex form stays inside the owner; it is referenced, not reused as the log key (width collision with D16).

### 4.3 Fact-log record — what is immutable

Every `log_record` is immutable after append. Allowed operations: APPEND. Forbidden: UPDATE, DELETE, in-place correction, rewriting `observed_at`.

Immutable per record: `log_seq`, `fact_id`, `document_id`, `observed_at`, `source_available_at`, `supersedes_fact_id`, `company_id`, `cluster_id`, `novelty`, `polarity`, `fact_key`, `provenance`, `evidence`, `payload_schema`, `quantity_fingerprint`, `reports_fact_id`, `linked_fact_ids`, `stated_deadline`, `next_expected_observation`.

`log_seq` is 1-based, dense, assigned at append. Records are totally ordered by `(log_seq)`. Tie-break for equal `observed_at` is `fact_id` lexicographic; the projector sorts that way, the writer must append in that order or the fold will still sort.

PIT: `observed_at >= source_available_at` (same law as `events.py` / event_workspace_build C4). A record with `observed_at` after the caller's `as_of_utc` is invisible to `F`.

### 4.4 Distinct fact vs revision (`fact_key`)

`fact_key = {company_id, template, slot}` is a structured equality key, not an id family.

Slot kinds:

- `t1_authorization_program`: `(action_type, horizon_token)` — the authorization itself.
- `t1_execution_under_program`: same program, execution quantities (masterplan §6 "authorization is not execution"; freeze near-duplicate T1-W2).
- `t2_metric_period_counterparty`: `(metric, fiscal_period_token, counterparty_company_id|null)`.
- `t3_object_counterparty`: `(event_kind, object_name, counterparty_company_id|null)`.
- `milestone_under_proposition`: `(milestone_name)` plus the parent proposition's `fact_id` carried in `reports_fact_id` of a manifestation or in `linked_fact_ids` of the milestone record.

Two records are **the same fact** (one is a revision of the other) iff `fact_key` is equal (deep equality of the object). They then share a supersedes chain.

They are **distinct facts** iff `fact_key` differs. A new magnitude/timing/commitment/counterparty that changes slot identity (new counterparty, new horizon, new object_name) is a new `fact_key` with novelty `new_magnitude_timing_commitment_counterparty` and `supersedes_fact_id=null`. A numeric restatement of the **same** slot is either `corrected_fact` (source says the prior number was wrong) or `new_magnitude_…` (source states a new authorized amount / new remaining capacity on the same program — still same `t1_authorization_program` key, chained via `supersedes_fact_id` only when the source is a correction; otherwise it is a new live record of the same key that **does not** retire the old one until a `corrected_fact` or `commitment_status=withdrawn` arrives).

Builder rule for same-key non-correction: do not supersede; both records remain; `live(key)` is the record with the greatest `(observed_at, fact_id)` whose novelty is not `commentary` and that is not itself superseded by a later `corrected_fact`. Named validator `V_LIVE`.

### 4.5 `corrected_fact` + `supersedes_fact_id` replay (never overwrite)

Preconditions (schema + named validators):

- `novelty=corrected_fact` ⇒ `supersedes_fact_id` is a 24-hex `fact_id` (freeze D16; schema allOf).
- That id must appear earlier in the log (`V_SUPERSEDES_EXISTS`).
- The superseded record must have the same `fact_key` (`V_SUPERSEDES_SAME_KEY`).
- Cycles are rejected (`V_SUPERSEDES_ACYCLIC`).
- The superseded record remains in the log forever (`V_NO_OVERWRITE`).

Replay procedure `live_payload(key, log, as_of)`:

1. Take records with that `fact_key` and `observed_at <= as_of`, ordered by `(observed_at, fact_id)`.
2. Build the chain: a record S retires T if `S.novelty=corrected_fact` and `S.supersedes_fact_id=T.fact_id` (or T is in the transitive supersedes closure of S).
3. The live record is the last record not in any supersedes closure. If none, the slot is absent (`field_absence.v1` reason `not_stated`).
4. All retired records stay queryable for "what was live at `as_of'`".

This is the same direction as `events.apply_transition(..., "corrected")` keeping `event_id` (`events.py:329-343`) and `pb_d_quality.append_source_correction` (`pb_d_quality.py:1087-1100`).

### 4.6 Provenance groups (conservative)

A **provenance group** is the independence atom for §5. Two manifestations are in the same group iff **either**:

1. `origin_document_id` is a string and equal (shared originating document: issuer PR, 8-K, exhibit), **or**
2. `root_family_id` is a string **and** `origin_claim_id` is a string and both equal (shared originating claim in the PB-D root sense, `pb_d_quality.py:17-22`).

`source_family` is a closed label on the record (`issuer_primary`, `regulator_filing`, `exchange_notice`, `wire_reprint`, `secondary_outlet`, `independent_measurement`, `unknown`). It does **not** by itself split or join groups.

**Worked collapse.** Issuer PR `doc_nvda_pr_20260928` is the origin. Reuters manifestation and Bloomberg manifestation both set `origin_document_id=doc_nvda_pr_20260928`, `origin_claim_id=claim_nvda_auth_150b`, `root_family_id=root_nvda_auth_20260928`, `source_family=wire_reprint`. Group id = `doc_nvda_pr_20260928`. One group. `member_count=3` (PR + two wires). A later 10-Q execution table is `origin_document_id=doc_nvda_10q_fy27q2` → a **different** group (`independent_measurement` or `regulator_filing`).

Title-similarity clustering (`qbus_news_cluster.py`) may still join the two wires into one `cluster_id`. That is level 1 (article). Provenance is level-2 independence. They are allowed to disagree: two independent measurements can share a cluster if titles match; two reprints of one PR can fail the title join and still share a provenance group.

HOLD-STRUCTURE-LEARNERS: do not learn a DAG over groups. The join rule above is the whole rule.

### 4.7 Thesis view fields — stored vs derived vs owner

| §5 field | Stored where | Derived how | Owner |
|---|---|---|---|
| original proposition | not stored as a row | first live `fact_revision` for the view key whose novelty ∈ `{new_magnitude_…, independently_observed_milestone}` at `decision_cut`; `plain_statement` is a bounded text_safe projection of the live payload's actor/action/object/amount (describe, not score) | fact log + news-impact leaf |
| decision cut | input to `F`, copied onto the view | caller supplies (PB-D `decision_cut` shape); must be `<= as_of_utc` | `pb_d_quality.py` coverage `decision_cut`; this program does not invent a second cut clock |
| supporting claim ids | ids live on log records | `owner_claim_ids` ∪ `fact_id` of live records with `polarity=supporting` | `event_claim.v1` (`issuer_profiles.py:231`) and log `fact_id` |
| contrary claim ids | same | `polarity=contrary` | same; T3 `contrary_mechanism_quote` presence forces contrary |
| root source families | provenance on each record | unique `{root_family_id, origin_document_id, source_family, member_count}` over live supporting records | `pb_d_quality.py` roots; fallback `origin_document_id` |
| exposure paths | not in the log | from `relationship_candidates` rows for `company_id` known at `as_of_utc`; if none, `field_absence.v1` subject `exposure_paths` reason `not_stated` | `relationship_candidates.py`; #6514 remains BLOCKED — no propagation_hypothesis |
| required assumptions | absences on live facts | every critical slot of the live payload that is `field_absence.v1` (e.g. T1 `executed_amount` absent until 10-Q) | frozen templates + `field_absence.v1` |
| current milestone evidence | milestone `fact_revision`s | live records with novelty `independently_observed_milestone` linked to the proposition | fact log |
| next expected observation | optional on a `thesis_link` or first fact | default ladder in §4.8: first milestone_name in the template bundle not yet in current milestone evidence; windows from `stated_deadline` / horizon | fact log + template bundle |
| deadline | `stated_deadline` on a fact_revision (ISO) or absence | view.deadline = max live `stated_deadline` if any string, else absence | T1 `horizon_period`; source-stated dates only |
| weakening conditions | **internal** array on the view | closed function of live facts (see enum); `armed=true` when the condition currently holds at `as_of_utc` | derived; **not** displayed under those names |

`material_delta_triggers` on the view is the set of triggers that fired **relative to the immediately prior view** at the previous `as_of_utc'` the caller names. If the caller passes no prior, the array is empty (first materialization is not a recompute).

### 4.8 Default staged bundles (next observation)

**T1 capital allocation (authorization program):** `announcement` → `executed_repurchase` → `net_dilution_reported`. Next watch after the §6 NVIDIA PR: `executed_repurchase` in the window through the stated horizon (fiscal 2028).

**T3 strategic / open-model (masterplan §7):** `announcement` → `artifact_available` → `license_stated` → `hardware_support_stated` → `independent_deployment` → `repeated_active_use` → `paid_bookings` → `reported_economics`. Downloads/stars are not milestones (MASTERPLAN.md §7).

**T2 demand/guidance:** `announcement` → `paid_bookings` / period-matched reported metric.

### 4.9 Material-delta recompute — closed enum and detection

Closed enum `material_delta_trigger` (schema):

| Trigger | Detection rule (deterministic) |
|---|---|
| `changed_numeric_terms` | A new `fact_revision` with same `fact_key` as a live fact, `quantity_fingerprint.form=present`, and `canonical_sha256` ≠ live fingerprint. |
| `new_independent_source` | A new record whose `provenance_group_id` is not in the set of groups already attached to live facts of this view. |
| `independently_observed_milestone` | New record with `novelty=independently_observed_milestone`. |
| `contradiction` | New live record with `polarity=contrary` on a `fact_key` that already has a live `polarity=supporting` record, OR `commitment_status` moves to `withdrawn` while a supporting live fact remains, OR `negated=true` vs live `negated=false` on the same key. |
| `missed_deadline` | View has a string `deadline`, `as_of_utc > deadline`, and the next-expected milestone is still absent from current milestone evidence. |
| `source_correction` | New record with `novelty=corrected_fact` and valid `supersedes_fact_id`. |
| `exposure_change` | Owner snapshot `relationship_candidates` canonical bytes for this `company_id` differ from the prior `owners_sha256` slice for that owner (or a previously present path's role/direction changes). If the owner is absent, this trigger never fires (typed absence is not a change). |
| `market_state_change` | Owner market-state artifact for the issuer's listed security changes between owner snapshots. LEAF reads; does not originate a market view. If the owner is not in the snapshot, the trigger does not fire. |

**Cosmetic rewording triggers nothing.** Detector: `novelty ∈ {new_reporting_of_old_fact, commentary}` AND `quantity_fingerprint` equal to live AND `provenance_group_id` already in the set. Named test `V_COSMETIC_NO_DELTA`: append such a record; `material_delta_triggers` of `F(log', owners, as_of)` vs `F(log, owners, as_of)` is `[]` and `live_fact_ids` unchanged.

**Unchanged mirrors trigger nothing.** Detector: two manifestations, same `origin_document_id`, same `quantity_fingerprint`, `source_family ∈ {wire_reprint, secondary_outlet}`. They share a provenance group (rule 1). Second append is `new_reporting_of_old_fact`. `V_MIRROR_NO_DELTA` same assertion as cosmetic.

Frontier/expensive review is **not** invoked unless `material_delta_triggers` is non-empty. That is a consumer policy on top of this store; this design does not originate the review.

### 4.10 Deadlines and the admitted scheduler

Name: **US-nightly engine lane**.

- Workflow: `.github/workflows/daily.yml:8-39` — cron `30 22 * * *` and `30 23 * * *`, ET-regime gated, 18:30 ET year-round.
- Python gate: `engine/ledger_lane.py:24-36` `nightly_advance_enabled()` when `COLLECT_LANE=nightly` (legacy `US_LANE=nightly`).

The projector is invoked from that lane with `as_of_utc` = the lane's as-of stamp (the same stamp news_event_ledger already accepts as `asof_utc`, `news_event_ledger.py:107-108,138`). This research creates no cron, no APScheduler, no metabolism window, and does not call `long_hold_clocks.entry_clock` / `thesis_clock` (those read `date.today()` and are display-only).

`missed_deadline` is therefore a property of `(view, as_of_utc)`, not a stored boolean.

### 4.11 Projector `F` (pure)

```
F(log: fact_log.v1, owners: OwnerSnapshot, as_of_utc: str) -> thesis_view.v1
```

`OwnerSnapshot` is a closed bundle of read-only payloads: identity map, qbus cluster rows, news_event_ledger rows, CI event/workspace/claims/facts/guidance if present, SourceSpan set, relationship_candidates, optional market-state blob, optional PB-D roots. Each owner payload is canonicalized; `owners_sha256 = sha256(canonical_json_bytes(owners))`. `log_sha256` likewise.

Steps:

1. Filter `log.records` to `observed_at <= as_of_utc`; sort `(observed_at, fact_id)`.
2. Index by `fact_key`; compute live set via §4.5.
3. Partition live records into thesis views by original proposition: a live `t1_*` / `t2_*` / `t3_*` fact is a proposition; `milestone_under_proposition` and `thesis_link` records attach via `linked_fact_ids` / `reports_fact_id`.
4. Fill the view fields per §4.7.
5. Compare to the prior view if the caller provided `prior_as_of_utc`; set `material_delta_triggers`.
6. Build `display` from windows and "what we are watching" templates. Internal `weakening_conditions` are not copied into `display`.
7. Encode with `canonical_json_bytes`.

Authority: `context_only`. `prophet_flags` all false. `unsolicited_instruction_detected` const false; if any free string fails `text_safe`, the record is not appendable (quarantine lives outside publishable templates, freeze D17).

### 4.12 Replay test (byte-identical)

Named test `V_REPLAY_BYTES`:

1. Fix `log`, `owners`, `as_of_utc` (no clock, no RNG).
2. `a = F(log, owners, as_of_utc)`; `b = F(log, owners, as_of_utc)`.
3. `canonical_json_bytes(a) == canonical_json_bytes(b)` (contracts.py:127-140).
4. Permute `log.records` then sort by `(observed_at, fact_id)` inside `F`; bytes still match (fold is order-canonical).
5. Prefix: `F(log[:k], owners, as_of)` equals the view at that prefix; appending a cosmetic/mirror record leaves bytes of the thesis fields other than `log_sha256` identical (`V_COSMETIC_NO_DELTA` on the view body excluding `log_sha256`).
6. Correction: append `corrected_fact`; live payload changes; the superseded `fact_id` remains in the log; replaying at `as_of` before the correction's `observed_at` returns the old live payload (`V_PIT_CORRECTION`).

### 4.13 Display-tier wording

Allowed: windows (`window_start`/`window_end`), "what we are watching", "the source states", "not yet observed in this store", "authorization is not execution".

Forbidden in `display.plain_status` and `display.what_we_are_watching`: falsifier, refutation, confidence, probability, score, target, fair value, likely, unlikely, will, certainty.

`weakening_conditions[].code` is internal storage. Display maps:

- `missed_stated_deadline` → "the stated window has passed without the next observation in this store"
- `contrary_independent_measurement` → "a separate source family reports a conflicting measurement; we are watching both"
- `source_correction_reduces_magnitude` → "the issuer restated the figure; the earlier figure remains in the log"
- `commitment_withdrawn` → "the source now states the commitment is withdrawn"
- `expected_observation_absent` → "the next observation in the bundle has not appeared in the stated window"

### 4.14 Named validators (Phase 3)

`V_LOG_SEQ`, `V_FACT_ID_UNIQUE`, `V_SUPERSEDES_EXISTS`, `V_SUPERSEDES_SAME_KEY`, `V_SUPERSEDES_ACYCLIC`, `V_NO_OVERWRITE`, `V_PIT_CLOCKS`, `V_LIVE`, `V_MANIFEST_POINTS` (manifestation `reports_fact_id` non-null and present), `V_COSMETIC_NO_DELTA`, `V_MIRROR_NO_DELTA`, `V_REPLAY_BYTES`, `V_PIT_CORRECTION`, `V_NO_FORBIDDEN_FIELDS` (grep `confidence|probability|score|price_target|fair_value|rating|likelihood|thesis_score` empty on schemas and payloads), `V_TEXT_SAFE`, `V_CI_EVENT_ABSENCE` (if payload type not in `EVENT_TYPES`, `ci_event_id` is `field_absence.v1`).

### 4.15 What this store must not do

- Originate a signal, size, rank, gate, or episode (Prophet flags false; freeze §9).
- Call `engine/news_llm.py` (`DNR:KILL-LLM-ORIGINATION`; freeze §9).
- Import `views.py` confidence metrics.
- Charter a thesis lobe (KILL-THESIS-LOBE).
- Learn a causal DAG (KILL-CAUSAL-DAG-ALPHA, HOLD-STRUCTURE-LEARNERS).
- Append to `news_event_ledger`.
- Touch PR #6514.

## 5. Worked cases (JSON)

Hashes below are `sha256(canonical_json_bytes(quantity_object))`. Absence fingerprints use `form=absent` and omit the hash.

Shared flags:

```json
{"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false}
```

### Case 1 — NVIDIA $150 billion authorization (MASTERPLAN.md §6), three levels

Issuer `cik:0001045810`. Primary document `doc_nvda_pr_20260928`. Cluster `ev2_a11c0e0000000001`. Authorization fact `fact_a11c0e000000000000000001`. Incremental $150B and remaining $235B through fiscal 2028; execution not observed.

```json
{
  "schema": "fact_log.v1",
  "authority": "context_only",
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false,
  "records": [
    {
      "log_seq": 1,
      "record_kind": "fact_revision",
      "cluster_grain": "fact_revision",
      "fact_id": "fact_a11c0e000000000000000001",
      "document_id": "doc_nvda_pr_20260928",
      "observed_at": "2026-09-28T14:05:00Z",
      "source_available_at": "2026-09-28T14:00:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_a11c0e0000000001",
      "novelty": "new_magnitude_timing_commitment_counterparty",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "capital_allocation_event.v1",
        "slot": {
          "kind": "t1_authorization_program",
          "action_type": "share_repurchase",
          "horizon_token": "FY2028"
        }
      },
      "provenance": {
        "origin_document_id": "doc_nvda_pr_20260928",
        "origin_claim_id": "claim_nvda_auth_150b",
        "root_family_id": "root_nvda_auth_20260928",
        "source_family": "issuer_primary"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_nvda_pr_20260928", "span_id": "span_aaaaaaaaaaaaaaaaaaaa"},
      "payload_schema": "capital_allocation_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1",
        "authority": "context_only",
        "reason": "not_stated",
        "subject": "ci_event_id",
        "detail": "news capital allocation is not in company_event EVENT_TYPES",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_nvda_auth_150b"],
      "quantity_fingerprint": {"form": "present", "canonical_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
      "reports_fact_id": null,
      "linked_fact_ids": [],
      "stated_deadline": "2028-01-30T00:00:00Z",
      "next_expected_observation": {"milestone_name": "executed_repurchase", "window_start": "2026-09-28T14:00:00Z", "window_end": "2028-01-30T00:00:00Z"},
      "unsolicited_instruction_detected": false
    },
    {
      "log_seq": 2,
      "record_kind": "manifestation",
      "cluster_grain": "article_manifestation",
      "fact_id": "fact_a11c0e000000000000000010",
      "document_id": "doc_reuters_nvda_auth_20260928",
      "observed_at": "2026-09-28T14:20:00Z",
      "source_available_at": "2026-09-28T14:18:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_a11c0e0000000001",
      "novelty": "new_reporting_of_old_fact",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "capital_allocation_event.v1",
        "slot": {"kind": "t1_authorization_program", "action_type": "share_repurchase", "horizon_token": "FY2028"}
      },
      "provenance": {
        "origin_document_id": "doc_nvda_pr_20260928",
        "origin_claim_id": "claim_nvda_auth_150b",
        "root_family_id": "root_nvda_auth_20260928",
        "source_family": "wire_reprint"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_reuters_nvda_auth_20260928", "span_id": "span_bbbbbbbbbbbbbbbbbbbb"},
      "payload_schema": "capital_allocation_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "ci_event_id", "detail": "news capital allocation is not in company_event EVENT_TYPES",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_nvda_auth_150b"],
      "quantity_fingerprint": {"form": "present", "canonical_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
      "reports_fact_id": "fact_a11c0e000000000000000001",
      "linked_fact_ids": [],
      "unsolicited_instruction_detected": false
    },
    {
      "log_seq": 3,
      "record_kind": "manifestation",
      "cluster_grain": "article_manifestation",
      "fact_id": "fact_a11c0e000000000000000011",
      "document_id": "doc_bloomberg_nvda_auth_20260928",
      "observed_at": "2026-09-28T14:25:00Z",
      "source_available_at": "2026-09-28T14:22:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_a11c0e0000000001",
      "novelty": "new_reporting_of_old_fact",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "capital_allocation_event.v1",
        "slot": {"kind": "t1_authorization_program", "action_type": "share_repurchase", "horizon_token": "FY2028"}
      },
      "provenance": {
        "origin_document_id": "doc_nvda_pr_20260928",
        "origin_claim_id": "claim_nvda_auth_150b",
        "root_family_id": "root_nvda_auth_20260928",
        "source_family": "wire_reprint"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_bloomberg_nvda_auth_20260928", "span_id": "span_cccccccccccccccccccc"},
      "payload_schema": "capital_allocation_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "ci_event_id", "detail": "news capital allocation is not in company_event EVENT_TYPES",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_nvda_auth_150b"],
      "quantity_fingerprint": {"form": "present", "canonical_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
      "reports_fact_id": "fact_a11c0e000000000000000001",
      "linked_fact_ids": [],
      "unsolicited_instruction_detected": false
    }
  ]
}
```

Level 1: three stories, one `cluster_id` (PR + two wires; title join). Level 2: one live fact `…0001`; two manifestations report it; **one provenance group** `doc_nvda_pr_20260928` (the two wires collapse). Level 3 view (as_of `2026-09-28T23:59:59Z`):

```json
{
  "schema": "thesis_view.v1",
  "authority": "context_only",
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false,
  "company_id": "cik:0001045810",
  "original_proposition_fact_id": "fact_a11c0e000000000000000001",
  "decision_cut": "2026-09-28T14:05:00Z",
  "as_of_utc": "2026-09-28T23:59:59Z",
  "original_proposition": {
    "payload_schema": "capital_allocation_event.v1",
    "plain_statement": "Issuer authorized an additional 150 billion dollars of share repurchase, remaining authorization 235 billion dollars, through fiscal 2028. Authorization is not execution.",
    "channel_hint": "capital_allocation",
    "commitment_status": "authorized",
    "negated": false
  },
  "supporting_claim_ids": ["claim_nvda_auth_150b", "fact_a11c0e000000000000000001"],
  "contrary_claim_ids": [],
  "root_source_families": [{
    "root_family_id": "root_nvda_auth_20260928",
    "origin_document_id": "doc_nvda_pr_20260928",
    "source_family": "issuer_primary",
    "member_count": 3
  }],
  "exposure_paths": {
    "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
    "subject": "exposure_paths", "detail": "no relationship_candidate row and PR 6514 remains blocked",
    "missing_fields": ["exposure_paths"]
  },
  "required_assumptions": [{
    "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
    "subject": "executed_amount", "detail": "authorization packet does not state completed purchases",
    "missing_fields": ["executed_amount"]
  }],
  "current_milestone_evidence": [{
    "fact_id": "fact_a11c0e000000000000000001",
    "milestone_name": "announcement",
    "observed_at": "2026-09-28T14:05:00Z",
    "provenance_group_id": "doc_nvda_pr_20260928"
  }],
  "next_expected_observation": {
    "milestone_name": "executed_repurchase",
    "window_start": "2026-09-28T14:00:00Z",
    "window_end": "2028-01-30T00:00:00Z"
  },
  "deadline": "2028-01-30T00:00:00Z",
  "weakening_conditions": [
    {"code": "missed_stated_deadline", "armed": false, "evidence_fact_ids": []},
    {"code": "expected_observation_absent", "armed": false, "evidence_fact_ids": []}
  ],
  "display": {
    "what_we_are_watching": "actual repurchases and net dilution through the fiscal 2028 window, not further reprints of the authorization",
    "windows": [{"label": "stated execution horizon through fiscal 2028", "start": "2026-09-28T14:00:00Z", "end": "2028-01-30T00:00:00Z"}],
    "plain_status": "the source states an authorization. completed purchases are not yet in this store. operating revenue impact is not established. surprise is unmeasured without a baseline."
  },
  "live_fact_ids": ["fact_a11c0e000000000000000001"],
  "cluster_ids": ["ev2_a11c0e0000000001"],
  "provenance_group_ids": ["doc_nvda_pr_20260928"],
  "material_delta_triggers": [],
  "log_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "owners_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
}
```

`material_delta_triggers` empty: first materialization. Appending a twentieth reprint (same fingerprint, same origin) fires `V_MIRROR_NO_DELTA`.

The quantity sha256 in this case is a placeholder; Phase 3 binds it to `canonical_json_bytes` of the T1 quantity slots. The empty-sha `e3b0c442…` here stands in so the schema parses; the builder replaces it with the real fingerprint of `{incremental:150e9, remaining:235e9, currency:USD, basis:{incremental,total}}`.

### Case 2 — NVIDIA open-model release (MASTERPLAN.md §7), three levels

Nemotron 3 announced 2025-12-15. Cluster `ev2_b22d1f0000000002`. Announcement fact `fact_b22d1f000000000000000001`. Later independent deployment `fact_b22d1f000000000000000002` (different provenance group). Thesis link `fact_b22d1f0000000000000000aa` joins them.

```json
{
  "schema": "fact_log.v1",
  "authority": "context_only",
  "prophet_flags": {"may_rank": false, "may_size": false, "may_gate": false, "prophet_authority": false},
  "unsolicited_instruction_detected": false,
  "records": [
    {
      "log_seq": 1,
      "record_kind": "fact_revision",
      "cluster_grain": "fact_revision",
      "fact_id": "fact_b22d1f000000000000000001",
      "document_id": "doc_nvda_nemotron3_20251215",
      "observed_at": "2025-12-15T16:00:00Z",
      "source_available_at": "2025-12-15T15:50:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_b22d1f0000000002",
      "novelty": "new_magnitude_timing_commitment_counterparty",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "strategic_product_partnership_event.v1",
        "slot": {"kind": "t3_object_counterparty", "event_kind": "product_release", "object_name": "Nemotron 3", "counterparty_company_id": null}
      },
      "provenance": {
        "origin_document_id": "doc_nvda_nemotron3_20251215",
        "origin_claim_id": "claim_nvda_nemotron3_announce",
        "root_family_id": "root_nvda_nemotron3",
        "source_family": "issuer_primary"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_nvda_nemotron3_20251215", "span_id": "span_dddddddddddddddddddd"},
      "payload_schema": "strategic_product_partnership_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "ci_event_id", "detail": "open-model release is not in company_event EVENT_TYPES",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_nvda_nemotron3_announce"],
      "quantity_fingerprint": {"form": "absent"},
      "reports_fact_id": null,
      "linked_fact_ids": [],
      "stated_deadline": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "stated_deadline", "detail": "the announcement does not state a commercial deadline",
        "missing_fields": ["stated_deadline"]
      },
      "next_expected_observation": {"milestone_name": "artifact_available"},
      "unsolicited_instruction_detected": false
    },
    {
      "log_seq": 2,
      "record_kind": "fact_revision",
      "cluster_grain": "fact_revision",
      "fact_id": "fact_b22d1f000000000000000002",
      "document_id": "doc_customer_10k_deploy_20260301",
      "observed_at": "2026-03-01T12:00:00Z",
      "source_available_at": "2026-03-01T11:00:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_b22d1f0000000002",
      "novelty": "independently_observed_milestone",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "strategic_product_partnership_event.v1",
        "slot": {"kind": "milestone_under_proposition", "milestone_name": "independent_deployment", "object_name": "Nemotron 3"}
      },
      "provenance": {
        "origin_document_id": "doc_customer_10k_deploy_20260301",
        "origin_claim_id": "claim_customer_nemotron_deploy",
        "root_family_id": "root_customer_deploy_202603",
        "source_family": "independent_measurement"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_customer_10k_deploy_20260301", "span_id": "span_eeeeeeeeeeeeeeeeeeee"},
      "payload_schema": "strategic_product_partnership_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "ci_event_id", "detail": "customer mention is not a company_event for this issuer",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_customer_nemotron_deploy"],
      "quantity_fingerprint": {"form": "absent"},
      "reports_fact_id": null,
      "linked_fact_ids": ["fact_b22d1f000000000000000001"],
      "unsolicited_instruction_detected": false
    },
    {
      "log_seq": 3,
      "record_kind": "thesis_link",
      "cluster_grain": "thesis_link",
      "fact_id": "fact_b22d1f0000000000000000aa",
      "document_id": "doc_nvda_nemotron3_20251215",
      "observed_at": "2026-03-01T12:00:01Z",
      "source_available_at": "2026-03-01T11:00:00Z",
      "supersedes_fact_id": null,
      "company_id": "cik:0001045810",
      "cluster_id": "ev2_b22d1f0000000002",
      "novelty": "independently_observed_milestone",
      "polarity": "supporting",
      "fact_key": {
        "company_id": "cik:0001045810",
        "template": "strategic_product_partnership_event.v1",
        "slot": {"kind": "t3_object_counterparty", "event_kind": "product_release", "object_name": "Nemotron 3", "counterparty_company_id": null}
      },
      "provenance": {
        "origin_document_id": "doc_customer_10k_deploy_20260301",
        "origin_claim_id": "claim_customer_nemotron_deploy",
        "root_family_id": "root_customer_deploy_202603",
        "source_family": "independent_measurement"
      },
      "evidence": {"form": "owner_span_ref", "document_id": "doc_customer_10k_deploy_20260301", "span_id": "span_eeeeeeeeeeeeeeeeeeee"},
      "payload_schema": "strategic_product_partnership_event.v1",
      "ci_event_id": {
        "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
        "subject": "ci_event_id", "detail": "thesis link does not mint a company_event",
        "missing_fields": ["ci_event_id"]
      },
      "owner_claim_ids": ["claim_nvda_nemotron3_announce", "claim_customer_nemotron_deploy"],
      "quantity_fingerprint": {"form": "absent"},
      "reports_fact_id": null,
      "linked_fact_ids": ["fact_b22d1f000000000000000001", "fact_b22d1f000000000000000002"],
      "unsolicited_instruction_detected": false
    }
  ]
}
```

Two provenance groups: issuer announcement vs customer 10-K. Recompute trigger on the third record: `independently_observed_milestone` and `new_independent_source`. Next watch becomes `repeated_active_use` then `paid_bookings`. Near-term earnings remain unquantified (`quantity_fingerprint.form=absent`). Display: "what we are watching is independent repeated use and paid bookings in the next reporting windows; repository stars are not in this store as profit evidence."

### Case 3 — correction / supersedes (remaining authorization restated)

Same key as Case 1. Issuer 8-K says remaining authorization is 210 billion, not 235. New `fact_id`, `novelty=corrected_fact`, `supersedes_fact_id=fact_a11c0e000000000000000001`. Record `…0001` stays in the log.

```json
{
  "log_seq": 4,
  "record_kind": "fact_revision",
  "cluster_grain": "fact_revision",
  "fact_id": "fact_a11c0e000000000000000004",
  "document_id": "doc_nvda_8k_corr_20261002",
  "observed_at": "2026-10-02T13:00:00Z",
  "source_available_at": "2026-10-02T12:50:00Z",
  "supersedes_fact_id": "fact_a11c0e000000000000000001",
  "company_id": "cik:0001045810",
  "cluster_id": "ev2_a11c0e0000000001",
  "novelty": "corrected_fact",
  "polarity": "supporting",
  "fact_key": {
    "company_id": "cik:0001045810",
    "template": "capital_allocation_event.v1",
    "slot": {"kind": "t1_authorization_program", "action_type": "share_repurchase", "horizon_token": "FY2028"}
  },
  "provenance": {
    "origin_document_id": "doc_nvda_8k_corr_20261002",
    "origin_claim_id": "claim_nvda_auth_150b_corr",
    "root_family_id": "root_nvda_auth_20260928",
    "source_family": "regulator_filing"
  },
  "evidence": {"form": "owner_span_ref", "document_id": "doc_nvda_8k_corr_20261002", "span_id": "span_ffffaaaaaaaaaaaaaaaa"},
  "payload_schema": "capital_allocation_event.v1",
  "ci_event_id": {
    "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
    "subject": "ci_event_id", "detail": "news capital allocation is not in company_event EVENT_TYPES",
    "missing_fields": ["ci_event_id"]
  },
  "owner_claim_ids": ["claim_nvda_auth_150b_corr"],
  "quantity_fingerprint": {"form": "present", "canonical_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"},
  "reports_fact_id": null,
  "linked_fact_ids": [],
  "stated_deadline": "2028-01-30T00:00:00Z",
  "unsolicited_instruction_detected": false
}
```

Replay at `as_of=2026-10-01T00:00:00Z` still live-selects `…0001`. Replay at `2026-10-02T13:00:00Z` live-selects `…0004`. Trigger: `source_correction` and `changed_numeric_terms`. Internal weakening `source_correction_reduces_magnitude.armed=true`. Display: "the issuer restated remaining authorization; the 28 September figure remains in the log."

### Case 4 — contradiction + absence (open-model contrary measurement; baseline absent)

A later independent source states production deployments moved to non-NVIDIA hardware. Distinct `fact_key` (same object, contrary polarity). Also an abstention: no baseline, surprise unmeasured.

```json
{
  "log_seq": 4,
  "record_kind": "fact_revision",
  "cluster_grain": "fact_revision",
  "fact_id": "fact_b22d1f000000000000000003",
  "document_id": "doc_rival_deploy_survey_20260615",
  "observed_at": "2026-06-15T09:00:00Z",
  "source_available_at": "2026-06-15T08:30:00Z",
  "supersedes_fact_id": null,
  "company_id": "cik:0001045810",
  "cluster_id": "ev2_b22d1f0000000002",
  "novelty": "independently_observed_milestone",
  "polarity": "contrary",
  "fact_key": {
    "company_id": "cik:0001045810",
    "template": "strategic_product_partnership_event.v1",
    "slot": {"kind": "milestone_under_proposition", "milestone_name": "independent_deployment", "object_name": "Nemotron 3"}
  },
  "provenance": {
    "origin_document_id": "doc_rival_deploy_survey_20260615",
    "origin_claim_id": "claim_rival_non_nvda_deploy",
    "root_family_id": "root_rival_deploy_202606",
    "source_family": "independent_measurement"
  },
  "evidence": {"form": "owner_span_ref", "document_id": "doc_rival_deploy_survey_20260615", "span_id": "span_11111111111111111111"},
  "payload_schema": "strategic_product_partnership_event.v1",
  "ci_event_id": {
    "schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
    "subject": "ci_event_id", "detail": "survey is not a company_event",
    "missing_fields": ["ci_event_id"]
  },
  "owner_claim_ids": ["claim_rival_non_nvda_deploy"],
  "quantity_fingerprint": {"form": "absent"},
  "reports_fact_id": null,
  "linked_fact_ids": ["fact_b22d1f000000000000000001"],
  "unsolicited_instruction_detected": false
}
```

View slice (contradiction + absence):

- `supporting_claim_ids` still include the announcement and the customer 10-K deployment.
- `contrary_claim_ids` = `["claim_rival_non_nvda_deploy", "fact_b22d1f000000000000000003"]`.
- `material_delta_triggers` = `["independently_observed_milestone", "new_independent_source", "contradiction"]`.
- `required_assumptions` includes baseline absence:

```json
{
  "schema": "field_absence.v1",
  "authority": "context_only",
  "reason": "not_stated",
  "subject": "baseline",
  "detail": "no prior_guidance, prior_reported_period, or prior_announced_programme is in the owner snapshot; surprise is unmeasured",
  "missing_fields": ["baseline"]
}
```

Display: "what we are watching is whether subsequent independent sources continue to report NVIDIA-hardware deployments or non-NVIDIA deployments, in the next two reporting windows. this store does not state which measurement is true."

Abstention is the lawful output when the extractor cannot bind a number or a CI event: `field_absence.v1`, never a guessed quantity, never a CIK-floor `evt_cik0000000000_…` (`events.py:182-200` plus freeze F1).

## 6. Failure modes and tripwires

| Failure | What it looks like | Tripwire |
|---|---|---|
| Correction overwrites | Live row mutated; old remaining-authorization bytes gone | `V_NO_OVERWRITE`; log length strictly increases; `V_PIT_CORRECTION` |
| Clock in the view | Two replays minutes apart change `missed_deadline` without a new record | `V_REPLAY_BYTES`; grep projector for `datetime.now`/`date.today` empty |
| Correlated reprints as independent evidence | `root_source_families.member_count` treated as 30 independent groups | `V_MIRROR_NO_DELTA`; group join on `origin_document_id` |
| Cosmetic rewording triggers frontier review | `material_delta_triggers` non-empty on same fingerprint | `V_COSMETIC_NO_DELTA` |
| New identifier family | `thesis_…` / `grp_…` / `view_…` appears | schema pattern walk; grep `thesis_` ids |
| CI event invented for news | `evt_cik0001045810_2026fy_news` | `V_CI_EVENT_ABSENCE`; `EVENT_TYPES` membership |
| Confidence/score leak | field named confidence/score/probability/target | `V_NO_FORBIDDEN_FIELDS`; freeze §0.3 |
| Thesis lobe rebuilt | new lifecycle service beside long-hold | KILL-THESIS-LOBE in review checklist |
| Structure learner on groups | NOTEARS/DAG over provenance | HOLD-STRUCTURE-LEARNERS |
| Scheduler invented | new cron in this LEAF | MASTERPLAN.md §5; only `daily.yml` + `ledger_lane.py` |
| Instruction injection via body | source says "ignore previous" and the projector obeys | `text_safe` not-patterns; record as injection finding; `unsolicited_instruction_detected` stays false on published records (quarantine outside templates, D17) |
| Display uses falsifier words | glance copy says "falsified" | display schema + wording grep on `display.*` |
| #6514 consumed | exposure_paths filled from propagation_hypothesis | freeze §1.1; absence unless relationship_candidates row exists |
| Leaf appends news ledger | `persist_kept_events` called from news_impact | freeze §9 |

## 7. Open questions for the seat (each with default)

1. **Same-key non-correction (new remaining capacity on the same program, source does not call it a correction).** Default: do **not** set `supersedes_fact_id`; `live` = latest `(observed_at, fact_id)`; keep both rows. Use `corrected_fact` only when the source states the prior figure was wrong. (Matches freeze T1-W2 "execution under the same program" as a distinct slot `t1_execution_under_program`.)
2. **Physical log format.** Default: append-only JSONL at `data/news_impact/fact_log.jsonl`, one `log_record` per line, reconstructed to `fact_log.v1` at read. Parquet is acceptable if column types match; JSONL is the boring baseline.
3. **Who writes `thesis_link` rows.** Default: the projector may emit them as derived records appended after a material milestone that links two live facts; a human review is not required for the link row. The view does not wait on them.
4. **Market-state owner for `market_state_change`.** Default: if no admitted owner is in the snapshot, the trigger never fires (honest absence). Do not read `long_hold_clocks` or `views.py` metrics.
5. **Polarity on mixed articles.** Default: `unclassified` unless `negated=true` (contrary) or a contrary-mechanism quote is span-backed; never a model vote.
6. **View cardinality.** Default: one view per `(company_id, original_proposition_fact_id)`. An issuer may have many views (authorization program ≠ open-model program). Do not blend them.
7. **Fingerprint algorithm.** Default: `canonical_json_sha256` of the live template's critical numeric slots only (T1: incremental/remaining/executed; T2: stated_amount; T3: stated_quantity), sorted keys. Cosmetic text is outside the fingerprint — that is what makes `V_COSMETIC_NO_DELTA` true.

---

Schemas: `fact_log.v1.schema.json`, `thesis_view.v1.schema.json` (Draft 2020-12). Parallel clusterer lane owns `cluster.py`; this design consumes `engine/qbus_news_cluster.py` as the existing owner and does not respecify join thresholds.
