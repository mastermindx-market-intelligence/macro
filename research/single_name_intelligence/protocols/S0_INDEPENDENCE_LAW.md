# S0 Independence Law: Single-Name Intelligence (Alibaba / Tencent)

**Status:** S0 FROZEN PROTOCOL. This is a research document and implements nothing.
**Task graph:** S0, domain O3. It satisfies acceptance case **A22**: "Linked counters, duplicate reports and overlapping outcomes do not inflate independent sample size."
**Companions:**
- **REG** = `S0_PROTOCOL_REGISTER.md`, the protocol rows.
- **SL** = `S0_SPLIT_AND_CONTAMINATION_LAW.md`, the split and retirement law (A23).

**Evidence base:**

| Source | Location | Commit |
|---|---|---|
| qledger, trial ledger, grading statistics | `engine/qledger.py`, `engine/trial_ledger.py`, `engine/grading_stats.py` | origin/main `31b9647872e1`. The diff over these paths is empty back to `e44069e306fd`, the evidence base V0 cites (V0 matrix L5). |
| V0 decisions | `research/single_name_intelligence/SNI_V0_EVALUATION_SUPPORT_MATRIX.md` and `SNI_V0_EXTENSION_DECISION.md` | on main (PR #8834) |
| Coverage profiles | `config/single_name_intelligence/coverage_profiles/alibaba.yml` and `tencent.yml` | `43251ca845b2` (PR #8837; byte-identical on origin/main `98a40e3f4b13`) |
| E0 and M0 qualifications | — | `43251ca845b2` (PR #8837) |

This document cites the profiles. It never edits them.

## 0. Authority (frozen)

| Scope | rank | gate | size | signal | escalation | trade |
|---|---|---|---|---|---|---|
| this law, every count it produces, every protocol that uses it | **false** | **false** | **false** | **false** | **false** | **false** |

An independence count is a measurement of how much evidence exists. It is never an input to a rank, gate, size, signal, escalation or trade.

## 1. Definitions

- **Counter.** A listing key exactly as it is written in a coverage profile:
  - alibaba: `adr_baba`, `hkd_9988`, `rmb_89988` (alibaba.yml L56, L32, L44);
  - tencent: `hkd_0700`, `rmb_80700` (tencent.yml L33, L45).

  These keys are labels. They are not canonical identifiers.
- **Issuer group.** All counters under one profile `issuer_key`: `alibaba` (alibaba.yml L13) or `tencent` (tencent.yml L13). Collapsing rows into an issuer group does not require a canonical id.
- **Event families.** There are exactly three, frozen: `results`, `capital_action` and `regulatory_material`. A protocol version freezes the rules that classify a row into a family. A row that the frozen rules cannot classify is not an event. It is listed and never counted.
- **Evidence row.** One input record: a filing, an exchange announcement, a wire story, a news item, a disclosure return or a price observation. Each carries a counter, a family candidate, a first-public-availability time `t_avail` and an evidence pointer.
- **Admissible `t_avail`.** `t_avail` must carry a `TIMESTAMP_QUALITY` (qledger L1185) of `CRAWL_BOUNDED`, `PUBLISHER_STATED` or `DISCLOSURE_DATE`. An event whose best evidence is `EVENT_DATE`, `SNAPSHOT_DATE` or `CORRUPTED` is excluded and listed. `t_avail` is never inferred from a price move.
- **Event.** One occurrence that survives step 2 (§3). It is anchored at the earliest admissible `t_avail` among its evidence rows.
- **Counting clock.** Declared per protocol version:
  - US legs use `MARKET_US`;
  - HK legs use `MARKET_HK`.

  Both clocks are resolved through `CLOCK_CALENDARS` (qledger L190). `MARKET_HK` binds the `_hk_calendar` import (L60, used at L193).
- **First session `s(c)`.** The first session on clock `c` whose regular open is strictly after `t_avail`.
  - A pre-open release maps to that same day.
  - A release during the session, during the HK midday break or after the close maps to the next session. The HK afternoon re-open is not a session open. This follows M0 §5 L174–L176, which states that midday-break announcements cannot be placed without intraday data.
  - A `DISCLOSURE_DATE` anchor maps to the first session strictly after the disclosure date.
  - Every event has an `s` on both clocks, whether or not it is graded on both.
- **Registered claims.** When a prospective claim is registered, the window that qledger resolves for it must begin at `s` on the claim's clock. That window is resolved through `_entry_anchor` (L2672) and `resolve_horizon_window` (L352), with fill convention `FILL_NEXT_BAR` (L2476). A claim whose resolved window does not begin at `s` is not registered, and it is listed.
- **Window `W_h(e, c)`.** Sessions `s(c)` through `s(c) + h` on clock `c`, inclusive. This is one session longer than the graded span, which is conservative for overlap. `h ∈ GRADE_HORIZONS = (5, 21, 63)` (L114), in the unit `HORIZON_UNIT_TRADING` (L141).
- **Cluster key.** The trade date of the opener's `s` on the protocol's counting clock. One date label is one cluster across clocks and across issuer groups.
- **Episode.** The unit of analysis. It is defined by step 4 (§3), separately for each `h`.
- **The four N quantities** (never interchangeable):

  | Quantity | Definition | Status |
  |---|---|---|
  | **literal row count** | input evidence rows before step 0 | printed for transparency only, never a sample size |
  | **honest-N(p, h, set)** | the number of **distinct episodes** counted for protocol `p` at horizon `h` in analysis set `set` (§4), after §3 has run in full | **the only sample N** |
  | **cluster-N(p, h, set)** | distinct cluster keys among those episodes; always ≤ honest-N | the clustering variable for uncertainty; distinct from `TrialLedger.effective_n` |
  | **trial count** | `TrialLedger.literal_n` (trial_ledger L210) and `TrialLedger.effective_n` (L214) for the protocol's family | the multiple-testing quantity, never a sample N and never added to one |

## 2. Principle: collapse on suspicion, link on evidence

The collapse rules below remove apparent independence wherever it is doubtful. If it is uncertain whether two rows are independent, they are collapsed.

**Linking** means pooling two counters' outcomes, using one counter's price for another counter's outcome, or attributing an event across issuers. Linking is refused unless an owner has recorded a canonical id for it. No issuer or security id is derived from a ticker, a name or a CIK. Where the profile records `UNRESOLVED`, that field stays `canonical_issuer_id: UNRESOLVED`.

The asymmetry is deliberate. Collapsing can only lower N, which errs toward caution. Linking can raise N or move outcomes between instruments, so it needs evidence.

## 3. Collapse order (runs in full BEFORE any N, CI, test or score)

The S1 runner implements these steps. qledger does not (§5). Each step records what it removed, and nothing is dropped silently.

**Step 0: admission.** A row enters only through a counter that the profile admits. Resemblance of ticker, name or CIK never admits a row. The following are excluded and listed:

| Excluded | Reason | Source |
|---|---|---|
| Tencent Music (`TME`) | a different issuer | tencent.yml L18–L19 |
| `KWEB` | a proxy and never a Tencent quote | V0 matrix row 19; `engine/hk_adr_bridge.py` L85 pairs 0700.HK with KWEB as `"proxy"` |
| `TCEHY` | not admitted | tencent.yml L499–L500 |

**Step 1: counter collapse.** Every row on any counter of an issuer group belongs to that issuer group. This holds even where `issuer_link` or `security_id` is `UNRESOLVED`. Collapsing without an id is allowed; linking without one is not (§2).

**Step 2: duplicate dedup (within family).** Rows that report the same fact are merged into one event, anchored at the earliest admissible `t_avail`. All of these are duplicates:
- the same release filed on several counters;
- a wire story or news item restating it;
- a clarification that adds no new fact.

If it is uncertain whether a later row adds a new fact, the row is collapsed. Execution returns of an announced buyback programme are evidence rows of the programme's single event. They are never events of their own.

**Step 3: same-session bundle.** A bundle is a connected component of events that share the same `s` on either clock.
- The bundle becomes one event of record. It takes the highest-precedence family present (`results` > `capital_action` > `regulatory_material`) and the earliest `t_avail`.
- If more than one family is present, the event of record is flagged `confounded`, with the list of the other families.
- The other members stay recorded as bundle members.

**Step 4: overlap absorption (per issuer group, per `h`, greedy).**
1. Order the events of record by `t_avail`. Break ties by family precedence, then by evidence pointer.
2. The first unassigned event **opens** an episode.
3. A later event `B` whose `s_B(c)` lies inside `W_h(opener, c)` on **either** clock is marked `absorbed_by_overlap`. It is recorded, never dropped and never counted.
4. There is no chaining. Only the opener's window absorbs.
5. The next unassigned event opens the next episode.

Consequences:
- The episode's outcome of record is the opener's outcome.
- A protocol counts only the episodes whose opener family is its own family.
- Every event lands in exactly one episode at each `h`.
- The windows of counted episodes are disjoint on both clocks, so their outcomes do not overlap.

**Step 5: cross-issuer.** Episodes of different issuer groups are never merged. A shared calendar date is handled through the cluster key only (§8).

**Step 6: horizons and legs are columns.** One episode graded at 5, 21 and 63 sessions is one episode with three outcome columns. One episode observed on several counters is one episode with several leg columns. N is reported separately for each `h`. N is never summed across horizons, counters or legs.

**Step 7: non-event protocols (REG P01, P02, P03, P09, P10).** The units are either the protocol's own registered claims (prospective arm) or declared rolling anchor dates (historical arm). In the historical arm, the greedy walk starts from the first eligible session of the split.

| Step | How it applies to non-event protocols |
|---|---|
| 0, 1 | apply unchanged |
| 2 | becomes claim-level count-once: qledger `_claim_id` (L1250) plus keep-first `register` (L2026) |
| 3 | does not apply |
| 4 | applies to the protocol's own units only, which yields non-overlapping blocks |
| 5, 6 | apply unchanged |

Uncertainty uses `grading_stats.block_bootstrap_ci` (L121) with block length ≥ `h`. The analysis set is ALL, and absorbed units are printed.

## 4. Analysis sets (all three reported; PRIMARY is pre-registered)

| Set | Contents |
|---|---|
| **PRIMARY** | all counted episodes, minus those flagged `confounded` |
| **SENS-A** | all counted episodes |
| **SENS-B** | PRIMARY, minus every episode that absorbed at least one member at that `h` |

A conclusion that holds only in SENS-A is not a finding. Every published result names its set, prints honest-N and cluster-N for all three sets, and prints the counts that were absorbed, confounded and excluded-and-listed.

## 5. What qledger does and does not do

- qledger gives **claim-level count-once only.** `_claim_id` (L1250) hashes a claim's identity, and `register` (L2026) and `register_batch` (L2077) keep the first row (V0 matrix row 16).
- qledger does **not** collapse counters, duplicate reports, bundles or overlapping windows. Those steps belong to this law and run in the S1 runner before anything is counted.
- Any N printed without this law applied must be labelled "literal row count". It must never be called a sample size.

## 6. Worked example: Alibaba (A22)

The example is symbolic and computes nothing. Assume the NYSE and HKEX calendars are both open on every date used. Holidays would move session numbers but not the logic. The counting clock is `MARKET_US`, because the only gradeable Alibaba counter is the US ADS.

**Input: 9 evidence rows (literal row count = 9).**

| row | counter | content | time | `s_US` | `s_HK` |
|---|---|---|---|---|---|
| a1 | `adr_baba` | results filing | 06:00 New York, date T. HK local is 18:00 or 19:00, after the HK close. | T | T+1 |
| a2 | `hkd_9988` | the same results, exchange announcement | same instant as a1 | T | T+1 |
| a3 | `rmb_89988` | the same announcement, attributed to the RMB counter | same instant | T | T+1 |
| a4 | `adr_baba` | wire story restating the results | later on T | — | — |
| a5 | `hkd_9988` | news item restating the results | T+1 | — | — |
| a6 | `adr_baba` | new buyback programme, announced in the same filing as a1 | same instant as a1 | T | T+1 |
| a7 | `hkd_9988` | execution return under the a6 programme | T+1 | — | — |
| a8 | `hkd_9988` | execution return under the a6 programme | T+2 | — | — |
| a9 | `adr_baba` | regulatory release | 07:00 New York, date T+9 | T+9 | T+10 |

**Step 0.** All rows are on admitted counters, so nothing is excluded.

**Step 1.** All 9 rows join issuer group `alibaba`. The profile records:
- the HKD counter's `issuer_link` as `UNRESOLVED` (alibaba.yml L39);
- the RMB counter's `security_id` and `issuer_link` as `UNRESOLVED` (L49, L52).

The collapse is allowed. Pooling or substituting 9988 or 89988 prices for the ADS is refused.

**Step 2.**
- E1 = {a1, a2, a3, a4, a5}, family `results`, anchored at a1.
- E2 = {a6, a7, a8}, family `capital_action`. The executions are evidence rows of the one programme.
- E3 = {a9}, family `regulatory_material`.

**Step 3.** E1 and E2 share `s_US = T` (and `s_HK = T+1`), so they form a bundle. The event of record is E1, flagged `confounded: [capital_action]`. E2 is a bundle member and opens nothing.

**Step 4.**

| `h` | E1 opens | E1's windows | E3 at `s_US = T+9`, `s_HK = T+10` |
|---|---|---|---|
| 5 | EP-A1 | US T..T+5, HK T+1..T+6 | outside both windows, so it opens EP-A2 |
| 21 | EP-A1 | US T..T+21 | inside the window, so it is `absorbed_by_overlap` into EP-A1 |
| 63 | EP-A1 | US T..T+63 | absorbed into EP-A1 |

**Counts (honest-N as PRIMARY / SENS-A / SENS-B):**

| protocol (opener family) | h = 5 | h = 21 | h = 63 |
|---|---|---|---|
| REG P04 `results` | 0 / 1 / 0 (EP-A1 is confounded) | 0 / 1 / 0 | 0 / 1 / 0 |
| REG P05 `capital_action` | 0 / 0 / 0 (E2 opens nothing) | 0 / 0 / 0 | 0 / 0 / 0 |
| REG P06 `regulatory_material` | 1 / 1 / 1 (EP-A2) | 0 / 0 / 0 (E3 absorbed) | 0 / 0 / 0 |
| issuer group, all families (SENS-A) | **2** | **1** | **1** |

- The literal row count is 9 at every horizon.
- Cluster-N for the issuer group is 2 at `h = 5` (dates T and T+9) and 1 at `h = 21` and `h = 63`.
- The nine rows never count as nine samples.
- The three counters never triple-count E1.
- E3 never adds a second sample at the horizons whose window it overlaps.

**Gradeability.** Only `adr_baba` (SEC:US-XNYS-BABA, alibaba.yml L61) can be graded, through `grade_claim` (L2698), and only after the REG §2 registration gate opens. A `hkd_9988` (SEC:HK-XHKG-09988, L37) claim would grade `primary_leg_refused` (`COHORT_ROWLESS_PRIMARY_REFUSED`, L2861) until V0 extension X7 lands (V0 matrix row 14). `rmb_89988` has no security id and is never a subject. Leg outcomes are columns of one episode, never extra N.

## 7. Worked example: Tencent (A22)

The example is symbolic, with the same calendar assumption as §6. The counting clock is `MARKET_HK`, because Tencent has no admitted US counter (§3 step 0).

**Input: 8 evidence rows (literal row count = 8).**

| row | counter | content | time (HK local unless stated) | `s_HK` | `s_US` |
|---|---|---|---|---|---|
| t1 | `hkd_0700` | regulatory announcement | 12:30 on date S, during the midday break | S+1 | S |
| t2 | `rmb_80700` | the same announcement on the RMB counter (tencent.yml L45) | same instant | S+1 | S |
| t3 | `hkd_0700` | news item restating t1 | later on S | — | — |
| t4 | `hkd_0700` | wire story restating t1 | S+1 | — | — |
| t5 | — | story about Tencent Music (TME) | S | — | — |
| t6 | — | KWEB price move | S | — | — |
| t7 | `hkd_0700` | clarification of t1 that adds no new fact | S+3 | — | — |
| t8 | `hkd_0700` | new buyback programme | 17:00 on S+8, after the HK close | S+9 | S+8 |

**Step 0.** t5 (a different issuer, L18–L19) and t6 (KWEB is a proxy, never a Tencent quote) are excluded and listed. Six rows remain.

**Step 1.** The six rows join issuer group `tencent`. The profile records:
- the issuer's `canonical_issuer_id` as `UNRESOLVED` (tencent.yml L15);
- the HKD counter's `issuer_link` as `UNRESOLVED` (L40);
- the RMB counter's `security_id` and `issuer_link` as `UNRESOLVED` (L50, L53).

The collapse is allowed. Linking is refused.

**Step 2.**
- E1 = {t1, t2, t3, t4, t7}, family `regulatory_material`, anchored at t1. The clarification adds no new fact, so it is a duplicate.
- E2 = {t8}, family `capital_action`.

**Step 3.** E1 (`s_HK = S+1`, `s_US = S`) and E2 (`s_HK = S+9`, `s_US = S+8`) share no session, so there is no bundle.

**Step 4.**

| `h` | E1 opens | E1's windows | E2 at `s_HK = S+9`, `s_US = S+8` |
|---|---|---|---|
| 5 | EP-T1 | HK S+1..S+6, US S..S+5 | outside both windows, so it opens EP-T2 |
| 21 | EP-T1 | HK S+1..S+22 | inside the window, so it is `absorbed_by_overlap` into EP-T1 |
| 63 | EP-T1 | HK S+1..S+64 | absorbed into EP-T1 |

**Counts (honest-N as PRIMARY / SENS-A / SENS-B):**

| protocol (opener family) | h = 5 | h = 21 | h = 63 |
|---|---|---|---|
| REG P06 `regulatory_material` | 1 / 1 / 1 (EP-T1) | 1 / 1 / 0 (EP-T1 absorbed E2) | 1 / 1 / 0 |
| REG P05 `capital_action` | 1 / 1 / 1 (EP-T2) | 0 / 0 / 0 (E2 absorbed) | 0 / 0 / 0 |
| REG P04 `results` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| issuer group, all families (SENS-A) | **2** | **1** | **1** |

- The literal row count is 8 at every horizon.
- Cluster-N for the issuer group is 2 at `h = 5` (dates S+1 and S+9) and 1 at `h = 21` and `h = 63`.
- The TME story and the KWEB move never enter the count.
- Five reports of one announcement count once.

**Variant: a clarification that does carry a new fact.** Suppose t7 had added a new fact and was published at 10:00 on S+3, during the HK session. It would then become its own event E3 (`regulatory_material`, `s_HK = S+4`, `s_US = S+3`). E3 would be absorbed into EP-T1 at every `h`, because S+4 lies inside HK S+1..S+6. The counts above would not change, except that SENS-B at `h = 5` would drop to 0 for P06.

**Gradeability.** Both Tencent legs are HK legs and are NOT SUPPORTED:
- the grader cannot read HK prices until X7 lands (V0 matrix row 14);
- a claim also needs an explicit HK bench (row 13).

No admitted US counter exists. These counts are therefore a descriptive census only, until the bridge exists. Tencent has no `canonical_issuer_id`, so it is excluded and listed from every cohort protocol's name axis (SL §3).

## 8. Cross-issuer: same-day shocks

Suppose one market-wide or sector regulatory shock produces an Alibaba event and a Tencent event whose openers share the same cluster date `D`.

- honest-N for the descriptive cross-issuer tally rises by **2**, one episode per issuer group, because they are never merged (step 5).
- cluster-N rises by **1**, because they share one cluster key.
- Uncertainty is clustered on the cluster key, so the shared shock is counted once in every CI.

A cohort pool across the two issuers is **refused** while Tencent's `canonical_issuer_id` is `UNRESOLVED`. Only the descriptive tally is permitted.

## 9. Enforcement

- The S1 runner applies §3 before any statistic is computed and writes its counts (removed, collapsed, bundled, absorbed, excluded-and-listed) into the result receipt (REG §5).
- An independence-law violation discovered after a split seal is contamination class **IDENTITY-REGROUP** (SL §7) and is handled by the visible retirement procedure (SL §8). It is never fixed silently.
- Any change to the family set, the classification rules, precedence, `s(c)`, `W_h` or the greedy rule is a design change. It requires a new protocol version under `DEC:PREREG-DESIGN-CHANGE-SUPERSEDES` (SL §6).
