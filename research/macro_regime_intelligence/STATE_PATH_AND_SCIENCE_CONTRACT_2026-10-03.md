# Granular Regime Intelligence — state, path and science contract (frozen 2026-10-03)

Programme: issue #8317 (Chairman assignment 2026-10-03). Parent architecture: PR #7088
(`research/macro_regime_intelligence/PROGRAM_ARCHITECTURE_2026-09-12.md` and
`R1_IMPLEMENTATION_PACKET_2026-09-12.md`, head `a6ccf23bfdee`, unmerged) and
`DEC:MACRO-REGIME-INTELLIGENCE-COMPOSITION`. Workstream: `WS:RATES-INFLATION-COMMAND`.
Decision record: `DEC:GRANULAR-REGIME-OUTLOOK-CONTRACT-V1`.

This is the contract a builder, a reviewer and a researcher work from. It freezes what the first
product vertical publishes, what it may never claim, and the rules every outcome study must
satisfy **before any new outcome is inspected**. It extends the parent packet and does not
replace it: where the parent already rules (one writer, the render-only return path, no
probability), this document adopts the ruling and adds the parts the programme assignment
requires — all ten state families, market-structure hypotheses, the science contract and the
seen-history register. Facts about `origin/main` were re-pinned at `6f5e78e94e88` on 2026-10-03
by two independent read-only censuses; anything inferred rather than read is marked.

Revision 2 (same day). An independent adversarial review of the first draft returned four
blocking findings and twelve further ones; all are addressed here and listed in §15. The owner
vocabularies behind Appendix A were audited from producer code by three further independent
read-only passes before the appendix was frozen.

Revision 3 (same day). An independent adversarial review of Appendix A returned four blocking
findings and twenty-two further ones; all are accepted and listed in §16. The appendix is
rewritten to one row convention (rule R-H), its guards are tightened from producer code, and a
hindsight coverage replay is added as a required slice (E1r).

Revision 3.1 (same day). The same reviewer re-read revision 3 against producer code and
returned one blocking finding, six further ones and five notes; all are accepted and listed in
§17. One condition (OD-6) is retired, one (TP-6) becomes an open row, the leader-damage guard
is rebuilt on the regime artifact's own embedded copy, and the replay rule (R-I) is made
one-directional.

Revision 3.2 (same day). Slice E0 repaired the first producer the appendix cites: the
transmission state now publishes no token and no number when its input is missing (PR #8348,
`698f58a0c74b`). That changed a cited decision function, so under rule R-E the mapping was
re-read against producer code and takes a new version, `VERDICT_MAPPING_V2`, before any
projection is built. No path, condition or reading changed. The changes are listed in §18.

Revision 3.3 (2026-10-04). The composer's independent review (PR #8380) found two silences in
this contract and they are closed here: a plain date stamp is a New York calendar day and is
judged against the New York date of the cutoff, and a projection built for a later completed
session is never a baseline. Neither touches the mapping: no path, condition, reading or family
changed, so `VERDICT_MAPPING_V2` stands. The changes are listed in §19.

## 0. Acceptance gates — the first vertical is not done unless

1. **Real path.** Change one transmission input in a real artifact shape, run the existing
   producer and Rates Command sequence, then the render-only stage: the page and the machine/AI
   readers both show the new condition with the **same** evidence ids, values, dates and
   qualifications. Repeating the render-only stage leaves every canonical data and ledger hash
   unchanged. A projection from an earlier generation never passes as the current read. An
   upstream failure still leaves a useful partial page and never fabricates a successful refresh.
2. **Three reading classes, proven without market luck.** `fits`, `does_not_fit` and `unknown`
   (§5.3) are each demonstrated on real current artifact shapes with one controlled perturbation
   per class; the perturbed input, the expected reading and the observed reading are recorded in
   the pull request. On unperturbed real data the only requirement is an honest output — whatever
   the day produces, including every reading `unknown`.
3. No date shown beside a value is a build or snapshot date presented as the reading's date (§4).
4. No number on the surface is a probability, a likelihood rank, a score across paths, a count
   compared between paths, or a count normalised to 100% (§5.3).
5. Every state family in §2 is present on the page either with evidence or with a plain-word
   reason it is not covered. Nothing is silently omitted.
6. **Failure cases** (the parent packet's list, kept whole) pass as tests: valid negative and
   zero yields; booleans masquerading as numbers; NaN and infinity; malformed mappings; stale
   policy beside fresh markets; missing labour data; a calculation date without an observation
   vintage; incompatible curve dates; future-dated observations; a known future-effective policy
   date distinguished from an observation; source corrections; mixed-generation publication; all
   inputs absent; exactly one invalid component with the other components usable. The cases use
   real current artifact shapes, not only idealised fixtures.
7. **Lane sequence.** After a nightly projection, a render-lane rebuild of the page — which does
   not rebuild the projection — produces the same section, labelled with the projection's own
   cutoff (§6).
8. **Design.** A mockup is committed and ratified by the operator before the section merges
   (§6, RIC-R12). Visual evidence exists for dark and light as two designs × EN and ZH × desktop
   1440 and mobile 390 (and the masterplan's 1280 and 375 widths as layout checks), posted in the
   pull request, with keyboard and touch navigation to each evidence source. The page's current
   design, accessibility and entitlement rules hold.
9. **Existing fields unchanged.** The board, scores, filters, ledgers and every existing reader
   behave as before: every existing field of the artifact and of each extended reader keeps its
   name, type and value. The additions are one new key in the artifact and additive fields in the
   readers (§12, E3).
10. Release proof is the served surface read back after a natural nightly run — not a fixture, a
    local build, a green check or a merge.

## 1. What this freezes, and what it does not create

Frozen here: the composed description and its owners (§2), the machine projection (§3), clocks
and statuses (§4), the path objects and how a reading is derived (§5), the user workflow and the
first surface (§6), the incumbent defects the first build must not inherit (§7), the scientific
contract (§8), the seen-history register (§9), naming rulings (§10), convergence with adjacent
carriers (§11) and delivery order (§12).

Not created: a regime engine, a market-truth plane, a history store, an evaluator, a graph, a
scheduler, a ledger, a source-identity registry, a probability, a ranking, or any authority. The
projection is **display and research tier**. It gates nothing, sizes nothing and promotes
nothing. Capital consequences stay behind Portfolio's own reserved gates.

Four objects are never conflated: the **current state** (what is observed now), **market-implied
pricing** (what prices embed), a **conditional path** (what would have to be true), and a
**statistical forecast** (a calibrated statement about an explicit target and horizon). A fifth,
**historical description**, is retrospective unless §8.2 qualifies it. Version 1 publishes the
first three. It publishes no forecast.

## 2. One composed description over existing owners

The projection cites owners; it does not recompute them. "Covered" means at least one owner field
is admitted in version 1. A family without an admitted field is published as `not_covered` with a
named reason — transparent missingness is part of the product.

| # | State family | Incumbent owner fields (artifact → field) | V1 coverage |
|---|---|---|---|
| 1 | Growth and inflation | `data/transmission/latest.json` → `state.inflation` (two verdicts and their numbers), `inflation_decomposition` (numbers); `data/regime/latest.json` → `conditions.labor_nowcast` (`read`; the three trends are bare signs, shown as evidence); `data/regime/regime_one.json` → `macro`, `tape` (numbers and sign-only quadrants, evidence); `data/release_forecast/latest.json` → `upcoming[]` (a schedule) | covered — real activity has no admitted owner verdict |
| 2 | Rates and discounting | transmission → `state.rates`, `state.expectations`, `breakeven_decomp`, `yield_curve.regime.term_premium_dir`, `yield_momentum.series`; `data/bonds/bond_health.json` → `fed_path.implied_cuts_12m` | covered |
| 3 | Liquidity and financing | regime → `conditions.financial_conditions.state`, `liquidity_quality` (`label` crosses the quantity of liquidity with its quality; reserve-balance and reverse-repo notes are numbers), `liquidity_quality.stress_overlay.confirming_stress` (its date is inherited from the liquidity block), `conditions.vintages` | partial — funding-market dysfunction has no admitted field |
| 4 | Market structure | regime → `conditions.complacency.breadth_div`; `data/market_state/latest.json` → `components[breadth]`; `data/dispersion/regime.json` → `state`. Named, not admitted: `site/basketdata/breadth_split.json` (its verdict is published only as text; its producer's position is unresolved). No market-level concentration owner exists | partial |
| 5 | Leadership and fundamentals | `data/leadership_crack/latest.json` → `state` — a fixed tracked AI-hardware cohort, never "all current market leaders". Evidence only: regime → `theme_revisions` (per theme, sign rules, no market-level verdict). Named for the later join: `site/marketdata/subsector_rotation.json`, `site/marketdata/themes_heatmap.json`, `data/index_leadership/*`; evaluator and shape vocabulary arrive with #8299 / #7976 (§11) | partial |
| 6 | Valuation and exposures | valuation and factor exposure exist per name only (`engine/valuation.py`, `engine/factor_exposure.py`); no market-level owner field | not covered |
| 7 | Volatility, correlation, positioning | market_state → `components[vol]`; dispersion → `avg_corr` (a variance-ratio proxy, a number, §10). Named, not admitted: `site/basketdata/vol_weather.json` chips (vocabulary not yet audited from producer code; producer position unresolved). Positioning proxies exist in `engine/systematic_flows.py` without a published market-level verdict | not_covered |
| 8 | Flows and reflexive effects | the ETF series in `engine/etf_flows.py` are price-and-volume proxies, not measured flows; no admitted flow owner | not covered |
| 9 | Cross-asset and regional | transmission → `dollar_channel.usd_dir` (evidence only until slice E0, Appendix A.2); `data/commodity/complex_latest.json` → `dollar_dir` and `data/commodity/latest.json` → `assets.oil.trend` (bare signs, evidence). Not admitted: `data/commodity/shock_state.json` (producer position unresolved) | not covered in version 1 — no admitted field until slice E0; scope is the United States; other regions are `not_covered`, never inferred |
| 10 | Change and outlook | this projection's `baseline`, `changes` and path objects | covered |

Rules:

- **Host and writer.** The projection is the top-level key `regime_outlook` of
  `data/rates_command/latest.json`. `scripts/build_rates_command.py` remains the sole writer. A
  pure deterministic helper owned by the same module is allowed; it is not registered as a state
  engine. No third artifact writer, no new endpoint, no model invocation.
- **Citation, not fusion.** Each evidence row copies an owner's native value with its unit and its
  own clock and names the owner field. The projection never averages families, never emits a
  universal regime score, and never reuses or renormalises the board's display scores
  (`hawk_score`, `ease_score`) or any sizing output (`gross_mult`).
- **One qualification vocabulary.** Evidence rows use the six statuses and the row fields of
  PR #8257's reader (`engine/neuralweb/regime_context.py`); §3 lists exactly which fields are
  shared, which this projection adds and which it omits, and §4 the shared status rule. That
  reader does not read the Rates Command artifact and its row qualifier is not yet a public
  function, so the first build carries a small helper in the Rates Command owner that mirrors the
  rule. Owed when #8257 lands: its qualifier exposed as a public pure function and used by both,
  plus a parity test — for every owner field both cite, the same artifact bytes and the same read
  instant give the same status, date and issues. Two divergent qualifications of one field are a
  defect.
- **Acyclic build, decided per field.** A field is admitted only if its producer never runs
  after `build_rates_command` in a lane that writes the projection (the nightly at
  `config/dag.yml` `build_rates_command`, and the weekly lane, which also runs that step and
  commits `data/`). Where a lane does not run a producer at all, the projection reads the last
  committed bytes and the row's own clock discloses their age. Appendix A records the position
  of each producer; a producer whose position could not be established is not admitted. A field
  whose producer runs later — for example `world_state.factor_weather`, composed after Rates
  Command — is not cited by the projection in version 1; it stays available to machine readers
  through #8257's reader.
  Published data files under `site/*data/` (`site/basketdata/breadth_split.json`,
  `site/basketdata/vol_weather.json`) are data artifacts with their own builders and may be cited
  under the same rule. The producer never reads the Monetary Policy workspace, the suite hub or
  any rendered page.
- **Scope label.** The projection carries `scope: "US"`. One US label never becomes a global one.

## 3. Machine contract — `regime_outlook.v1`

```
regime_outlook:
  schema_version: "regime_outlook.v1"
  scope: "US"
  analysis_cutoff: <UTC instant the inputs were snapshotted>
  built_at: <UTC instant written>
  mapping_version: "VERDICT_MAPPING_V2"   # Appendix A; its sha256 is recorded beside it
  inputs: { <artifact_id>: { path, sha256, read_status } }
  evidence_clock_range: { oldest, newest, by_clock_semantics: { <semantics>: n } }
  families: [ { family_id, coverage: covered|partial|not_covered, reason, evidence_ids: [...] } ]
  evidence: [ {
      id, family_id, evidence_family_id,
      kind: level|change|velocity|acceleration|categorical|market_pricing|schedule,
      values, unit, window, scope,
      owner_verdict,                      # the owner's own token, with its verdict class (App. A)
      status, issues: [...], notes: [...], currentness_certified: false,
      source: { artifact, pointer, sha256, clock_semantics, as_of, precision,
                age_calendar_days, future_dated, known_at, available_at,
                expected_us_session, session_relation, reference_period } } ]
  conditional_paths: [ {
      path_id, family: rates|market_structure,
      conditions: [ { condition_id, statement_id, evidence_ids: [...],
                      reading: fits|does_not_fit|not_discriminating|unknown, reason } ],
      family_readings: [ { evidence_family_id,
                           reading: fits|does_not_fit|mixed|not_discriminating|unknown } ],
      watch: [ { condition_id, next_scheduled, owner_ref } ] } ]
  baseline: { analysis_cutoff, us_session, evidence: { <id>: { values, owner_verdict, status, as_of } } }
  changes: [ { evidence_id, change_kind, from, to } ]      # always against `baseline`
  historical_comparisons: { status: "absent", reason: "history_not_qualified", qualification: {...} }
  forecast_distributions: { status: "absent", reason: "no_admitted_owner" }
  conditional_exposures: [ { path_id, statement_id, basis, owner_ref } ] | { status: "absent", reason }
  authority: { may_rank: false, may_gate: false, may_size: false,
               may_trade: false, may_forecast: false, may_escalate: false }
  tier: "display_research"
```

Field rules:

- `analysis_cutoff` is the information boundary: nothing first available after it may appear. The
  projection has **no single "as of" date**. `evidence_clock_range` is computed only from rows
  whose `clock_semantics` is `source_observation_date`; other rows are counted in
  `by_clock_semantics`, not folded into the range.
  - **Clock rule for stamps (revision 3.3).** An owner stamp that is a plain date (`YYYY-MM-DD`)
    names a US-session calendar day in America/New_York. Its `future_dated` flag and its
    `age_calendar_days` are judged against the **New York date of the cutoff** — the same clock
    `session_relation` uses — never against the cutoff's UTC date, so a stamp for the next New
    York day is future-dated even after 00:00Z has turned the UTC date. An offset-aware instant is
    future-dated when it is after the cutoff instant; its age is the New York day difference. A
    change in a stamp's precision alone (a date becoming an instant on the same New York day) is
    never a later observation.
- `inputs.<id>.sha256` is the hash of the bytes read at the cutoff — provenance for the cited
  inputs only. It is not compared between builds and nothing keys on it (an artifact that embeds
  its build instant changes hash on every build). Change detection works on evidence values,
  verdicts, statuses and clocks (`baseline`, §6). No source-identity registry is minted and no
  owner is asked for a new generation reference.
- `evidence_family_id` groups evidence that is not independent. Nominal yield, real yield and
  breakeven are one family (breakeven is their difference); overlapping financial-conditions
  indices are one family; several tenors of one curve are one family. Any count shown to a user or
  a machine counts families, never rows. `family_readings` is the roll-up Appendix A defines
  (A.5): where a family's conditions disagree inside one path the family reads `mixed`, and it
  is never resolved by preferring one owner.
- **Relation to the #8257 row, stated exactly.** Shared, same names and meanings: `status`,
  `scope`, `unit`, `values`, `issues`, `notes`, `currentness_certified` (always `false` — a
  source saying "fresh" describes its last build, not this read) and, inside `source`,
  `artifact`, `pointer`, `sha256`, `clock_semantics`, `as_of`, `precision`, `age_calendar_days`,
  `future_dated`, `known_at`, `available_at`, `expected_us_session`, `session_relation`. The six
  `authority` flags are #8257's, all false. Added by this projection: `id`, `family_id`,
  `evidence_family_id`, `kind`, `window`, `owner_verdict`, `source.reference_period` (the month
  or quarter a low-frequency print refers to; `null` when the owner does not publish it) and the
  top-level `tier`. Omitted: nothing — #8257's issue
  tokens (for example `availability_after_observation_cutoff`, `ambiguous_duplicate_chip`) are
  carried unchanged, and this projection's own tokens (§4) extend that list.
- The key is additive. No existing field of the artifact is renamed, removed or re-typed —
  including `forward.p_quad` / `next_quad_probs` in their own owners.

## 4. Clocks and statuses

`status` is exactly the #8257 vocabulary: `missing`, `unknown_date`, `future_dated`, `stale`,
`partial`, `available`, decided in that order by the same rule. Finer reasons travel in
`issues[]` and are never collapsed into each other or rendered as a reassuring reading. #8257's
own tokens are carried unchanged; this projection adds `not_covered`, `malformed`, `conflicted`,
`provisional`, `insufficient_history`, `rights_blocked`, `no_owner_verdict`,
`sign_only_verdict`, `age_exceeds_max`, and the tokens Appendix A's guards produce:
`owner_default_on_missing`, `possible_missing_as_zero`, `contains_sign_only_leg`,
`owner_sign_inconsistent`, `owner_did_not_write`, `no_admitted_owner_field` and
`vocabulary_not_audited`. The list is closed; a new token is a new mapping version.

`clock_semantics` uses #8257's two values and adds three it has no case for:
`source_observation_date` (the date the reading refers to), `owner_snapshot_date` (the last row
of a feature frame or a build date, shared by every field in the block),
`release_schedule_date` (a future release), `authored_date` (a human- or model-written date) and
`unknown`.

Re-pinned facts at `6f5e78e94e88`:

- Observation clocks exist only on `yield_momentum.series.<tenor>` (`as_of`, `endpoint_dates`,
  `last_observed`), `market_state.input_vintages.<k>`, `regime.conditions.vintages.<k>`,
  `commodity/shock_state.oil.ts` and `release_forecast.upcoming[].release_date` (a schedule).
- `transmission.state.rates`, `state.inflation`, `state.expectations`, `inflation_decomposition`,
  `conditions.labor_nowcast`, `commodity.assets.oil` and the term-premium fields carry **only**
  the frame date (`engine/rate_inflation_transmission.py:593`). Monthly and quarterly prints sit
  under a daily frame date with no reference month and no release date.
- Known stale or skewed on the pin date: `shock_state.oil.ts` 2026-09-18; `policy/intel.as_of`
  2026-07-13 (authored); `input_vintages.ebp` 2026-07-01; `dollar_channel.asof` is
  newest-of-pairs and can read a weekend date while the frame reads the prior session.

Rules:

1. An `owner_snapshot_date` or `authored_date` is never rendered as the date of a reading. The
   surface says which snapshot carried the value and that the reading's own date is not published.
2. A row whose only clock is `owner_snapshot_date` may be shown as current context, but it cannot
   be the basis of a "what changed" attribution (§6), a history claim or a transition claim.
3. **Age is checked, not only the producer's flag — one rule, owned by the #8257 reader.** At
   its reviewed head (`d64d9dec`) that reader marks a row `stale` only when the producer says so,
   so an artifact months old but never flagged stays `available`. Its repair (ruling K4, in
   progress on its own carrier) adds one named maximum age per source — seven calendar days for
   daily-cadence sources, a larger value only where the producer's documented cadence is slower,
   each citing the producer — and reports a breach with the existing `stale` status and the issue
   `age_exceeds_max`. This projection adopts that table and rule unchanged and introduces no
   threshold of its own: the helper mirrors the constants, and the parity test (§2) pins them
   equal. It is a disclosure rule, not a tuned parameter. Until the repaired reader is available
   the projection applies only the producer's flag and says so (`notes`), rather than inventing
   an allowance. A stale row stays visible and labelled; it never yields `fits` or
   `does_not_fit`.
4. Clocks are preserved, never manufactured. If an owner does not publish a reference period or a
   release date, the projection publishes `null`, not an estimate.
5. Giving the snapshot-only blocks their own reference and release clocks is owner work in
   `engine/rate_inflation_transmission.py` and the regime conditions producer (slice E0). The
   projection does not paper over it.

## 5. Paths

### 5.1 Rates paths (from the parent architecture, unchanged)

| `path_id` | Assumption under examination | Discriminators |
|---|---|---|
| `orderly_disinflation` | Inflation pressure eases without broad deterioration in labour or credit. | inflation composition and expectations; hiring, income, claims; credit conditions; real-rate velocity |
| `growth_deterioration` | Lower yield pressure comes with weakening activity and financing conditions. | labour breadth; real activity; credit spreads and funding; earnings context; dollar behaviour |
| `renewed_inflation_pressure` | Price pressure broadens or persists rather than a single transitory print. | inflation breadth; wages and services; breakevens (with liquidity caveats); policy repricing; oil mechanism |
| `long_end_premium_shock` | Long-end yields rise for reasons the near-term policy path does not capture. | curve decomposition; term-premium model evidence; issuance and demand; cross-model disagreement |
| `technical_pause` | A price or yield reversal is visible but durable fundamental confirmation is incomplete. | multi-horizon yield turns; market breadth; positioning; subsequent macro confirmation |

### 5.2 Market-structure hypotheses (the extension the programme requires)

| `path_id` | Assumption under examination | Discriminators (each named by its construction, §10) |
|---|---|---|
| `continued_selective_concentration` | Index strength stays carried by a narrow group while the rest lags. | cap-weight versus equal-weight relative; participation on a named denominator; leader persistence; credit and funding stability |
| `genuine_broadening` | Participation widens with fundamental support. | participation rising on a fixed historical universe; revision breadth; dispersion falling without correlation spiking |
| `internal_leadership_handoff` | Leadership rotates inside a healthy theme or market. | leader turnover inside a theme; theme-level participation holding; no absolute damage to the cohort |
| `deterioration_spreading_to_leaders` | Weakness in non-leaders reaches the leaders. | absolute damage (not relative lag) among leaders; funding and credit worsening; correlation rising with dispersion |

These four are path objects of the same shape — hypotheses with evidence, not a second state
registry. Appendix A turns each path's discriminators into stated conditions and admits the
owner verdicts that exist today (participation against the index high, the breadth component,
damage in the tracked AI-hardware cohort, credit stress and financial conditions); the
dispersion tercile and the correlation proxy are shown as evidence. Every other discriminator — cap-weight against equal-weight, leader persistence
and turnover, revision breadth, participation on a fixed historical universe, positioning —
has no market-level owner verdict on `origin/main` (the F1 census, §12) and reads `unknown`
with the reason `no_admitted_owner_field`: the hypotheses are visible, the evidence gap is
visible, and nothing is invented to fill it.

### 5.3 How a reading is derived — and what it may never become

- **A path is its stated conditions.** Each path is a short list of plain, positive statements,
  each naming one side of one owner's band ("the labour read is firm", "real yields are
  falling"). Appendix A freezes, for every condition, the one owner field it reads and which of
  that owner's tokens are the side the statement names (`fits`), the opposite side
  (`does_not_fit`), or the owner's middle (`not_discriminating` — the owner's dead-band token,
  such as "stable", "anchored" or "mixed", which says nothing about the statement in any path).
  Statements are never negated: "is not cooling" would count the middle as fitting (Appendix A,
  R-H). Anything else is `unknown`, with a reason.
- **A reading is a statement about wording, not about cause or likelihood.** `fits` means only
  that the owner's published token is one the statement names. It does not say the path is
  occurring, is more likely, or that the evidence causes it. The parent architecture's working
  tokens "supports / contradicts" are renamed `fits` / `does_not_fit` for this reason, and
  "neutral" is replaced by the defined `not_discriminating`.
- **Admission by verdict class.** Appendix A classifies every owner token from producer code:
  - `banded` — the owner decided the token with its own published threshold or dead-band. It may
    yield a reading.
  - `composite` — the owner's rule combines several inputs. It may yield a reading; the rule is
    quoted in the appendix.
  - `sign_only` — a two-token verdict whose opposite tokens meet at a single cut, with no middle
    token and no dead zone (the financial-conditions `trend` is `tightening` whenever the change
    is above zero). It is shown as evidence with its number and the issue `sign_only_verdict`;
    the reading is `unknown`. A composite whose legs each keep a dead zone between their two
    votes, and whose opposite tokens are separated by a middle token, is not `sign_only` even
    when one of its cuts sits at zero; the appendix quotes such cuts. The projection adds no
    dead-band of its own — a banded verdict is owner work in the owner.
  - `no_verdict` — a number with no owner token. Evidence only; reading `unknown`; issue
    `no_owner_verdict`.
  - `free_text` — never read.
- No new threshold is introduced to make a card decisive. A row whose status is not `available`
  yields `unknown` with that status as the reason. Two owners that disagree (on the pin date:
  `dollar_channel.usd_dir` flat versus `complex_latest.dollar_dir` strengthening) are shown as a
  disagreement, not resolved by preference.
- **The table is itself an authored construction, and says so.** It is a display-tier
  vocabulary: versioned (`VERDICT_MAPPING_V2`, its sha256 recorded in the projection), one
  producer citation and one line of rationale per row, reviewed independently before any code is
  written against it. It has never been tested against outcomes and makes no such claim. Any use
  beyond display — a rank, a gate, a transition claim, a study target — is a new construction
  under §8 with its own preregistration. A change to the table is a new version, reported in
  `changes` as `mapping_version_changed`; it is never a silent edit and never described as a
  change in the market.
- **Not a probability, and not a scoreboard.** Paths are overlapping hypotheses: not mutually
  exclusive, not exhaustive, not ordered by likelihood, never normalised. Inside one path's card
  the surface may state how many evidence families — groupings, not independent witnesses
  (Appendix A, R-D) — fit, do not fit, are mixed, or
  are unknown for that path's own conditions. Those counts are not comparable between paths — paths have
  different numbers and kinds of conditions — and the surface says so. No cross-path total,
  table or sort exists in the page or in the machine projection, and no synthesis sentence may
  compare paths ("more evidence for", "best supported", "leading", "most likely"). Paths render
  in the fixed order of §5.1 then §5.2.
- `regime_one.forward.p_quad` is an accruing probability owned by Regime One. It is never read
  into a path, never relabelled, and never displayed by this projection.
- A later calibrated forecast is a separate object with its own explicit target partition, issued
  by the existing model and evaluation owners through their own gates (§8).

## 6. The user workflow and the first surface

One workflow: **Now → What changed → Paths → History → Exposures → Watch**.

- **Now.** A plain-word synthesis of the covered families, then each family with its evidence,
  each row carrying its own date and qualification. Families that are not covered say so in plain
  words. Contrary evidence sits beside supporting evidence, never behind a fold that hides it.
- **What changed.** Differences between this projection and its `baseline`, classified as
  `observation_advanced`, `value_revised` (same reading date, different value — a source
  revision), `owner_verdict_changed`, `became_stale`, `became_available`, `became_unavailable`,
  `clock_only`, `issues_changed` (an `available` row became `partial` with its values, verdict and stamp
  unchanged — it acquired an issue), `mapping_version_changed`, or `unattributed` (the value changed but its source
  date is not published). A revision, a late print or a clock-only change is never described as a
  regime transition.
  **Baseline rule.** The baseline is the newest committed projection whose completed US session
  is strictly earlier than this build's. A rebuild within the same session — a second nightly
  attempt, the weekly lane, a recovery run — carries the stored baseline forward unchanged and
  never promotes the same session's earlier build to "previous". A `previous` whose completed
  session is **later** than this build's is never its baseline and lends nothing it carries: the
  baseline is then absent with reason `previous_from_later_session` (revision 3.3). The baseline travels inside the
  artifact (`baseline`), following the incumbent board's own same-day rule
  (`engine/rates_inflation_command.py`, the `prev_state` carry), so the comparison never depends
  on git history or on which lane ran last. The first projection ever written has no baseline and
  says so; it reports no changes.
- **Paths.** Each card: the assumption, "Why this fits", "What does not fit", "What we are
  watching". Evidence is reachable by keyboard and touch to its source and date.
- **History.** Version 1 publishes an honest absence: history appears only when it can be
  reconstructed from what was known at the time (§8.2). A retrospective description, when added,
  is labelled as hindsight on the surface itself.
- **Exposures.** Conditional statements only, each typed by `basis`: `arithmetic_identity` (bond
  price moves opposite to yield), `owner_measured_sensitivity` (cites an existing owner artifact),
  or `mechanism_hypothesis` (labelled unmeasured; may not name a beneficiary security, theme or
  size). No beneficiary claim ships without the asset-response gate (§8.5). Version 1 may be an
  absence plus identities.
- **Watch.** For each path, the unknown and pending conditions with the next scheduled release
  from `release_forecast.upcoming[]`, plus the inputs currently stale.

Wording law (the design doctrine governs; this adds the programme's limits): plain words in EN
and ZH; no internal state or study names, raw slugs or untranslated statistics on the glance tier;
no refutation vocabulary on user surfaces — paths are "windows, not certainties"; every panel
answers "so what do I do", including "watch — the evidence does not yet discriminate". Dark and
light are designed separately. Machine readers receive the projection itself, not a paraphrase.

**First surface: `site/transmission.html`, linked from Macro Command.** Reasons: the accepted
Rates & Inflation Command masterplan designates that page as the command's home; the parent
packet already rules a render-only return path there; and it is an existing, maintained page
reached by deep links, so no navigation family or header changes. The alternatives are closed:
`DNR:HOLD-UD-B1-PRIMARY-MACRO-MIGRATION` suspends stacking a second regime surface above the
established `macro.html` dashboard (it routes "any compact global successor through
`markets.html`", which is a compact global surface, not this US rates-and-structure workflow);
and the Macro Command suite is a sealed, hash-checked workspace contract whose hub "owns no
producer and publishes no state of its own". The assignment asks for the surface to be linked
from Macro Command: the link is part of this vertical's acceptance, delivered as a deep link by
the suite's owner under its own contract (slice H1) — until it lands, the vertical is reported
as built and reachable by direct link, not as complete.

Build rules for that surface:

- **The section renders only from the projection.** Every value, date and qualification in the
  section comes from `regime_outlook`; the section never combines a value from the transmission
  contract the rest of the page is built from. A mixed-generation read is therefore impossible
  inside the section by construction, and the section is labelled with the projection's own
  `analysis_cutoff` ("read prepared …"), not with the page's build time.
- **Every lane that builds the page behaves the same way.** `scripts/build_transmission.py`
  runs in four places: the nightly (before `build_rates_command`), and the weekly, engine-render
  and render lanes. In each, the default build renders the section from the committed projection
  it finds. To publish the same night's projection, a render-only stage of the same script is
  bound in `config/dag.yml` after every `build_rates_command` node in a lane that commits the
  page (the nightly and the weekly). That stage reads the prepared transmission contract and the
  projection and writes the page only: no feature recomputation, no collector refresh, no data
  artifact, no ledger append. Render lanes that do not rebuild the projection re-render the same
  section from the same committed projection — same content, same cutoff label.
- **Degraded states are explicit.** Projection absent, unreadable or of an unknown schema
  version: the section shows a plain "being updated" state and nothing else. Projection older
  than the newest completed US session (the nightly did not finish): the section shows that
  projection as the previous read, labelled with its own cutoff and a "newer read is being
  prepared" note. Neither state is ever styled as a current read, and neither blocks the rest of
  the page.
- The section is one include partial with its styles in governed CSS, so the active
  transmission-page lanes collide on a single include line.
- **Mockup first, operator ratification (RIC-R12).** The masterplan's surface-merge law requires
  the transmission page's rebuild to be "mockup-first with operator ratification" with browser
  verification. A new workflow section on that page is within the purpose of that law, and this
  contract does not argue otherwise: the exact markup and styles are pinned in a committed
  mockup, the operator ratifies the mockup, and only then does the section merge. The
  ratification gates slice E2 alone — E0, E1, E3 and the mockup itself proceed without it.
- **Access.** The section inherits the page's current access class, pinned from the page's
  existing gate in the E2 packet before design; it creates no entitlement tier. In the machine
  path, the paid/guest partition of #8257 is preserved: the guest path still makes zero reads.
- `macro.html` gains at most a deep link from its existing Fed Path card. The Macro Command
  suite's Monetary Policy workspace keeps its existing Rates Command projection.

## 7. Incumbent defects the first build must not inherit

All are on `origin/main` and are repaired in their owners in slice E0, with tests. Until an
owner is repaired, the projection applies the stated guard and never the defect.

In `engine/rates_inflation_command.py`:

1. **Snapshot date as freshness.** The board's `asof` is the maximum of candidate dates and falls
   back to today's date when none is present; change detection, the forward log's keep-first rule
   and the registry freshness check key on it. The projection keys on `analysis_cutoff` and
   per-evidence clocks instead. (Recorded on the parent as
   `DSC:RIC-WRAPPER-DATE-IS-NOT-JOINT-EVIDENCE-FRESHNESS`.)
2. **`usd_dir` fingerprint.** `compact_state.usd_dir` stores the whole policy-row object. The
   correct owner field is `transmission.dollar_channel.usd_dir`.

In the transmission producers (`engine/rate_inflation_transmission.py`, `engine/yield_curve.py`,
`engine/transmission_context.py`), found by the Appendix A audit:

3. **A missing input reads as the calm middle state.** `(x or 0)` comparisons return `steady`,
   `stable`, `anchored`, `flat` or `neutral` when the input is absent, and a missing core PCE
   reads `below target`. A middle token is therefore not evidence that anything was measured.
   Guard: Appendix A names, per field, the token the owner returns when its input is missing
   (the default token). The projection admits a default token only when the number it was
   decided from is published and finite beside it; otherwise the reading is `unknown` with the
   issue `owner_default_on_missing`. For the banded fields a non-default token cannot be
   produced by a missing input. Two owners are the exception. The breakeven cause classifier treats a
   missing input as "condition not met" and falls through to a later cause; it is evidence
   only (Appendix A.2) and is displayed only when all five of its inputs are published. The
   leader-damage monitor writes nothing when too few members are fresh, leaving the previous
   file in place; it is guarded on every token (Appendix A, R-B). Repair: the owner returns no
   token when its input is missing. Repaired for the transmission state by PR #8348 (`698f58a0c74b`):
   its five verdicts are `null` when their input is missing. The guard stays, because a file
   written before the repair can still carry the old default word.
4. **A missing number is published as 0.00.** Several `state` values are written through
   `round(x or 0, 2)`. Guard: those fields are cited as evidence only where the audit confirms a
   real value; an exact 0.00 on a field in the audit's list carries the issue
   `possible_missing_as_zero` and yields no reading. Repair: the owner publishes `null`. Repaired
   by PR #8348: the eight numbers are `null` when missing, so from mapping version 2 a
   published 0.00 is a reading and the issue is no longer raised (§18).
5. **The verdict's own date and number are not carried.** `dollar_channel.asof` is the newest
   date across currency pairs, not the date of the broad-dollar series behind `usd_dir`, and the
   rate of change behind the token is nulled. The monthly and quarterly blocks carry only the
   frame date (§4). Guard: `clock_semantics: owner_snapshot_date`. Repair: per-field observation
   dates and reference periods in the owner.
6. **Two vocabularies under one field name.** `state.rates.turn_watch` (`extreme_watch`, peak
   side only) and `yield_momentum.series.<tenor>.turn_watch` (`extreme_high_watch`, both sides)
   use different code paths. The projection cites only the per-tenor field, and reads an empty
   value together with that tenor's `status` and `path_qualified`, because an empty value also
   means "not qualified" or "insufficient history".

## 8. Scientific contract — frozen before any new outcome is inspected

### 8.1 Targets and clocks

Every study preregisters, before unblinding: the observed variable; the market, cohort or
instrument; the horizon; the decision cutoff; the source knowledge time; the outcome maturity; and
the event definition. Four target classes are kept apart and never substituted for one another:

| Class | Question | Success is not |
|---|---|---|
| T1 current-state accuracy | Does the description at the cutoff agree with what later vintages show for that date? | anticipation |
| T2 transition detection | Was a defined change of state flagged, with what lead, miss and false-alarm burden? | a retrospective label matching itself |
| T3 explicit-horizon forecast | Is a stated probability for a stated target and horizon calibrated and better than baselines? | current model membership |
| T4 action utility | Does acting on the state beat static beta and simple trend/volatility rules after costs? | a correct macro call |

- Current model membership is not a future probability. Predicting a house label is not predicting
  the economy.
- Macro-state forecast horizons are 1, 3, 6 and 12 calendar months, owned by Regime One; a study
  preregisters exactly one of them as primary and reports the others, if at all, as secondary
  with their multiplicity. Market outcome horizons are chosen from 5, 21 and 63 sessions: one
  primary horizon is preregistered, at most two secondary horizons are reported with their
  multiplicity, and no horizon grid is searched.
- An outcome window may not begin before the first session whose open follows the decision
  cutoff, and its entry price is that session's open (or the first price after the cutoff that
  the study's price source actually publishes, named in the preregistration). A close-to-close
  window that starts on the signal date is admissible only as a descriptive consistency
  statistic, labelled `non_executable_clock`, never as utility. The
  programme introduces no new market-outcome clock: leadership studies use the clock the #8299
  evaluator's owner ratifies (§11).

### 8.2 Information basis

Three classes, stated on every result: `issued_record` (a genuinely issued historical record with
an immutable issue time), `information_set_reconstruction` (rebuilt from vintages whose
availability is qualified), and `retrospective_description` (revised data; description only, no
skill claim). The qualification flags are those PR #8304 publishes —
`historical_replay_eligible`, `market_input_availability_verified`,
`fitted_model_and_state_history_verified`, `actual_historical_issuance_verified` — all false on
the pin date. Normalisers, imputation, feature selection, model state and calibrators are fitted
inside each training partition. Lookback dependence, release revisions, historical constituents,
the price basis and missing sources are preserved. An observed series is never extended backwards
with an unlabelled proxy.

### 8.3 Comparators

Frozen before the study: persistence / no change; unconditional frequency; simple trend and
volatility; the accepted incumbent; and, for transitions, an empirical transition matrix fitted on
the training window only. Paired ablations hold universe, execution horizon, availability and
outcomes fixed. Rate direction and bond-price direction are scored separately.

### 8.4 Statistical honesty

The preregistration is a committed file merged to `origin/main` before any outcome it concerns
has matured or been inspected; its merge commit is the study's clock. It states the rule that
separates or merges adjacent dates into episodes (minimum gap, and what joins two flagged
stretches) before any outcome is seen.

Walk-forward splits with overlap purge and an embargo at least as long as the horizon; era and
episode analysis; dependence-aware intervals. The sample size reported is the number of distinct
episodes, not adjacent daily rows. Every candidate and trial is recorded in the existing trial
ledger with its multiplicity — never a selected positive cell. Reported: calibration, false-alarm
burden, lead time, missed transitions, duration and interval errors, abstention and per-era
failure. Before any conclusion is presented it is run against the motivating live exemplars and
the current regime, and it states whether today is in-sample of the winning cell and who is
missing from the panel.

### 8.5 Economic utility and asset response

Static beta, simple volatility/trend risk management and the state-conditioned approach are
evaluated separately with realistic delays, spread and slippage, turnover, carry and exposure
constraints. A macro forecast can be right and already priced. An asset-response claim is
instrument-specific, conditional, and states uncertainty, starting conditions and costs. No sizing
or leverage derives from model prose. This is a study programme, not autonomous trading.

### 8.6 Result policy

Useful descriptive context ships without an alpha claim. A forecast needs explicit evidence or a
visibly bounded experimental status. Weak methods are demoted or retired and the baseline stays.
A null as a standalone signal may be retained as a confluence input; a kill closes the specific
construction tested, not the search space. Negative results are kept and printed. Advancement
gates are separate and sequential: descriptive context → forecast → asset response → capital
adoption.

## 9. Seen-history register (append-only)

Data whose outcomes have been inspected can never again serve as an untouched holdout for the same
question family. It may be used for development and diagnostics only. An out-of-sample claim
requires either data dated after the study's preregistration commit, or a partition attested as
never outcome-inspected — attested by a named independent reviewer who is not the study's
author, with this register consulted and cited in the preregistration.

| Id | What has been seen | Carrier |
|---|---|---|
| SH-1 | Daily SPY, RSP, QQQ, IWM, SOXX and DFII10, 2007-01-03 to 2025-12-31, ten-session outcomes under eight or more policies | #8303 |
| SH-2 | The September 2026 candidate shard | #8303 |
| SH-3 | The signal archive, 60,538 rows (rich regime axes on 583) | #8301 / #8303 |
| SH-4 | `regime_v2_pit` through 2026-07-02: 1,618 initial-vintage-input rows, 23,895 revised-input rows, 252 with no active component; all four qualification flags false | #8304 |
| SH-5 | Prophet phase 21: 209 outcome-inspected episodes | Prophet / #8303 |
| SH-6 | French 49-industry reference, 2016–2025 — computed; adjudication blocked on its carrier; treated as seen | #8299 |
| SH-7 | Incumbent subtheme scorecard, 47 dates through 2026-10-01 (rank correlation negative, not significant, at 5/10/21/63 sessions) | #8299 |
| SH-8 | The rejected and negative studies of #7909 — frozen; no retuning, no re-search of favourable cells | #7909 |
| SH-9 | The episodes that motivated the programme's question, including the contrasting bond and metals paths around 2018–2019 and 2022. They belong in the acceptance set and are not independent test cases after being used to design a rule | parent architecture (#7088) |
| SH-10 | The Rates Command forward log — every window already issued and graded by the nightly | Rates & Inflation Command |
| SH-11 | Regime One's accruing `forward.p_quad` record — outcomes accrue nightly and are visible to anyone reading the artifact | Regime One |
| SH-12 | The mapping coverage replay dates — 2018-10-31, 2019-08-30, 2022-06-30 and 2022-10-31 — read through the mapping version in force when the replay runs (`VERDICT_MAPPING_V2` from revision 3.2; no replay was run under version 1) on revised data (Appendix A, R-I). Registered here before the replay is run; the dates already sat inside SH-9 | this contract (slice E1r) |

Every study that inspects an outcome appends a row here in the same pull request as its result.

## 10. Naming and collision rulings

- `hidden_fragility` is the complacency state owned by `engine/conditions.py` (calm volatility
  with weak breadth or widening credit), consumed by `engine/risk_state.py`. No other construction
  may use that token. A different construction is named for what it measures.
- There is no bare "breadth". Each measure is named by construction and denominator (share above
  the 200-day average on a stated universe; equal-weight minus cap-weight return; a split by
  cohort). Likewise there is no single "leadership": index leadership, subsector rotation and the
  #7976 repricing shape appear under their own names and are never merged into one score.
- `avg_corr` in the dispersion owner is a variance-ratio correlation proxy and is labelled so.
  Index volatility and constituent dispersion are different statistics and are never subtracted
  from each other.
- Flows are measured only from flow data. Returns, volume and relative strength are not flows.
- Every study names its price basis and its adjusted / total-return convention.
- Source-local theme identifiers are not fuzzily renamed into canonical themes.

## 11. Convergence with adjacent carriers

Rulings for this programme and requests to the carriers' owners; nothing here edits another
owner's branch.

- **#8299 (subtheme replay qualification).** Its evaluator `engine/subsector_track_record.py` is
  the leadership evidence substrate. This programme adds no leadership evaluator and adopts the
  outcome clock its owner ratifies. Its recorded denied data and result-inspection operations stay
  denied and are not rerouted.
- **#7976 (theme repricing context).** After its requested changes close, its shape vocabulary is
  the display-tier supplier for family 5. Regime conditioning reaches it by reading
  `regime_outlook`, not by a fork.
- **#8303 (Prophet regime × indicator × timeframe).** Its observation-basis diagnostic (completed
  bars versus as-of snapshot) is a required disclosure on any multi-timeframe evidence. Its
  two-variable ETF state is a study construction, not a regime definition, and is subject to §10.
  It consumes #8301's axis-scope rules unchanged.
- **#8257 / #8301 / #8304 / #8306.** The reader, the axis-scope rule, the window-basis provenance
  and the mechanism-evidence path are prerequisites; each stays `HOLD-FOR-SOL` until its release
  owner rules. This programme brings them to their gates and does not release them.
- **#7871 / #7165.** The cycle-vintage collector and the release-target vintage store are the only
  collectors for their families. No duplicate collector, credential copy or current-vintage
  backfill.
- **#7441.** Its natural-versus-coached evaluator is the answer-quality evaluator. Synthetic
  transport tests are not live-answer proof.
- **Shared CI manifest.** `.github/ci/legacy-jobs.yml` has one writer at composition time; each
  carrier's enrolment is re-expressed on current main in sequence.

## 12. Delivery slices and order

| Slice | Content | Depends on |
|---|---|---|
| E0 | Repair the incumbent defects in their owners (§7): the Rates Command date and `usd_dir`; missing inputs returning no token and `null` instead of a middle state or 0.00; per-field observation dates and reference periods for the snapshot-only transmission and labour blocks | — |
| E1 | The `regime_outlook` key: families, evidence, rates paths and conditions per Appendix A, baseline and changes, watch; the failure-case suite; the §7 guards; the rule-pin test (R-E) and the mapping lint test (R-H) | Appendix A reviewed; E0 for the repaired fields (the guards cover the rest) |
| E1r | The mapping coverage replay (Appendix A, R-I): four fixed dates, labelled hindsight, a wording and guard check only; its output is committed beside the mapping | E1 |
| E2 | The section on `transmission.html` via the render-only path; visual evidence matrix | E1; E1r; committed mockup ratified by the operator (§6) |
| E3 | Machine and AI readers extended in place, existing fields unchanged: `market_packet._rates_block`, `world_state._compose_rates_command`, and `mastermind_context._summarize_rates_command` | E1 |
| F1 | Census and joins for families 4–8; admit owner fields into the market-structure hypotheses | — (parallel) |
| D1 | Historical qualification: collector integration (#7871), window basis (#8304), axis scope (#8301) | their release owners |
| G1 | Answer evaluation with natural regime questions (#7441) | E3 |
| G2 | One preregistered baseline-first transition study | D1; §8; §9 |
| H1 | Cross-product context — Macro Command workspace reference, Prophet, Terminal, Portfolio — without re-originating truth | E3; each owner's contract; reserved gates for capital |

The descriptive vertical (E0–E3) does not wait for predictive evidence. The numerical study (G2)
waits for data qualification and preregistration.

## 13. Golden scenarios → what each must prove

1. High real yields, concentrated strong revisions, weak non-leader participation → the surface
   explains selective strength and its evidence limits; it does not answer only "risk-on".
2. Narrow leadership with stable credit versus with worsening funding and absolute damage →
   concentration and transmission risk are distinguished by different discriminators.
3. Falling yields in disinflation versus in a growth scare → different conditional implications,
   and the missing discriminators are named.
4. Similar index volatility with different dispersion and correlation → unlike statistics are not
   subtracted; index calm alone is not safety.
5. Price participation improving while revision breadth rolls over → the disagreement is shown.
6. A new leader inside a healthy theme versus the theme breaking → turnover, diffusion, valuation
   and flow evidence stay separate.
7. A source correction, a late revision, a future timestamp or an absent cohort → the output
   changes or abstains for the right reason and invents no transition.
8. Regions in different local states → one summary plus local differences.
9. Mobile and desktop, natural and coached questions → the same qualifications and dates survive.

Scenarios 3, 7 and 9 are provable on the E0–E3 vertical. Scenarios 1, 2, 4, 5 and 6 depend on
families 4–7 and are proven when F1 admits their fields; scenario 8 needs regional owners. Until
then the correct behaviour for each is a visible, reasoned absence.

## 14. Open questions for owners

- #8299 owner: which market-outcome clock is canonical — close-to-close or next-open — and is the
  French 2016–2025 result treated as seen after recovery?
- #8303 owner: adopt a construction-specific name in place of `hidden_fragility` for the ETF
  state.
- Regime One owner: the additive forecast contract that would let a calibrated distribution
  replace the `forecast_distributions` absence.
- Macro Command suite owner: whether and how the Monetary Policy workspace references the new key.
- Release owner: sequencing of the four held candidates once their repaired heads are reviewed.
- Operator: ratification of the committed mockup of the `transmission.html` section before
  slice E2 is assembled (§6). Slices E0, E1 and E3 do not wait for it.
- Transmission and conditions owners (slice E0): publish which leg decided
  `stress_overlay.confirming_stress`, a banded verdict in place of each bare-sign trend, and
  the band id behind the breadth-split stance, so that those rows can leave "evidence only".
- Commodity owner: which lane writes `data/commodity/shock_state.json`, so its position
  relative to `build_rates_command` can be recorded.

## 15. Change log — revision 2

The independent red-team review of revision 1 returned sixteen findings. Each is listed with the
change that answers it.

| # | Severity | Finding | Change |
|---|---|---|---|
| 1 | blocker | A render lane that rebuilds the page without rebuilding the projection made the section vanish or pass an old projection as current; the proposed `inputs.generation` reference did not exist. | §6: the section renders only from the projection and is labelled with the projection's own cutoff; a render-only stage never recomputes it. Gate 7 tests the lane sequence. The invented generation reference is removed (§12, E0). |
| 2 | blocker | The masterplan's condition for the first surface — a committed mockup ratified by the operator — was dropped. | §6 and gate 8 restore it; slice E2 is gated on the ratified mockup (§12); the ratification is listed in §14. E0, E1 and E3 do not wait for it. |
| 3 | blocker | A hand-written table from owner tokens to "supports / contradicts" is a model introduced through the back door. | §5.3: readings are renamed `fits` / `does_not_fit` and defined as statements about wording; tokens are admitted by verdict class from producer code; the table is a versioned, display-tier authored construction (Appendix A) that claims no outcome evidence, adds no threshold and must be reviewed before code. |
| 4 | blocker | The projection's own age rule and the #8257 reader's rule could qualify the same field differently. | §4 rule 3: one rule, owned by the #8257 reader, adopted unchanged; a parity test pins the mirrored constants (§2). |
| 5 | should | The parent packet's failure cases were silently reduced. | Gate 6 carries the parent list whole and requires real artifact shapes. |
| 6 | should | Gate 2 could pass or fail on the day's market. | Gate 2 now requires one controlled perturbation per reading class and accepts any honest output on unperturbed data. |
| 7 | should | "Verbatim" reuse of the #8257 row was false in detail. | §3 lists the shared fields, the additions and the omissions exactly; §4 carries #8257's issue tokens unchanged and lists this projection's additions. |
| 8 | should | The family table under-claimed coverage against #8257 and dropped a required distinction. | §2 table rewritten from three producer-code audits and the F1 owner census; liquidity quantity against quality, and the tracked cohort against "all leaders", are stated in the rows. |
| 9 | should | Per-path counts invited a ranking. | §5.3: counts exist only inside one path's card, per independent evidence family, never across paths; no cross-path total, table, sort or comparative sentence in the page or the machine projection. |
| 10 | should | "Previous" was undefined for same-session rebuilds. | §6 baseline rule: the newest committed projection from a strictly earlier completed session, carried inside the artifact. |
| 11 | should | Seen-history and episode counting had loopholes. | §8.4: preregistration merged to `origin/main` before any outcome matures, with a preregistered episode separation rule; §9: attestation by a named independent reviewer, and rows SH-9 to SH-11. |
| 12 | should | Two assignment requirements were narrowed without saying so (the Macro Command link; entitlement). | §6 states the link is part of this vertical's acceptance and how it is delivered; gate 8 and §6 keep the page's entitlement rule and create no new tier. |
| 13 | nit | Entry price and primary horizon unspecified. | §8.1: entry at the first post-cutoff session open; one preregistered primary macro horizon. |
| 14 | nit | The registry row for `macro.html` was over-read. | §6 quotes the row for what it says and rests the choice on scope. |
| 15 | nit | "Existing fields unchanged" was stated two ways. | Gate 9 and slice E3 use one statement: every existing field keeps its name, type and value. |
| 16 | nit | Wrong function name for the third reader. | §12 names `mastermind_context._summarize_rates_command`. |

Revision 2 also adds what the audits found and the review did not ask for: the six incumbent
defects in §7, the default-token guard, and Appendix A.

## 16. Change log — revision 3

The independent red-team review of Appendix A (revision 2) returned `REQUEST_CHANGES`: four
blocking findings, fifteen further ones and seven notes. It reproduced the worked example's
arithmetic and concluded that a reader would still have been misled on the pin date — the
`orderly_disinflation` card showed three evidence families fitting while real yields stood at a
five-year extreme and were rising. Every finding is accepted. Each is listed with the change
that answers it.

| # | Severity | Finding | Change |
|---|---|---|---|
| B1 | blocker | The same owner token was mapped two ways, and negated statements ("is not cooling") absorbed the owner's middle token into `fits`, tilting negatively phrased paths. | New rule R-H: every condition is a positive statement naming one side of one owner's band; the middle token is `not_discriminating` in every row; rows that read the same field are identical or exact mirrors. Slice E1 ships a lint test for it. A.4 is rewritten to the rule. |
| B2 | blocker | Rule R-C guarded only half of `confirming_stress`: a `false`, and a `true` with NFCI above zero, could rest on the bare-sign leg. | R-C rewritten: `true` is admitted only when the published numbers prove the banded credit leg fired; `false` only when they prove neither leg could have fired; otherwise `unknown`. |
| B3 | blocker | Non-default cause-badge tokens can arise from a missing input (`_classify_cause` treats a missing number as "condition not met" and falls through). | R-B extended: any cause token is admitted only when all five published co-state numbers are finite. §7 item 3's sentence that a non-default token needs no check is corrected. |
| B4 | blocker | Discriminators the parent promises were missing from several paths, which tilted the pin-date cards. | A.4 adds OD-7 (real yields), TP-6 (breadth; made an open row in revision 3.1, §17) and a visible `unknown` row for every discriminator in §5.1 and §5.2 that has no admitted field. |
| S1 | should | `labor_nowcast.read` is not "two-of-three banded votes"; two legs cut at zero. | A.1 quotes the rule exactly, including the zero cuts. `sign_only` is redefined (§5.3) as a two-token verdict split at a single cut with no middle; the labour read stays admitted because every leg has a dead zone between its two votes and the opposite tokens are separated by `labor mixed`. |
| S2 | should | "Above target" did not match the owner's band. | RI-2 reads "above the owner's 1.7–2.3% band". |
| S3 | should | OD-6's wording claimed more than the owner's rule. | OD-6 states the owner's attribution in the owner's terms, names `growth` as a residual, is grouped with credit and funding, and carries the co-state guard. Superseded in revision 3.1: OD-6 is retired (§17, C-B1). |
| S4 | should | GB-2 read a level where the discriminator is a change. | GB-2 is retired as a reading; the discriminator is an `unknown` row and the dispersion tercile and correlation proxy are evidence in **Now**. |
| S5 | should | SC-1 and GB-1 overstated the owner's construction and are not independent. | SC-1 uses the owner's exact construction; R-D and the GB-1 rationale state that the breadth component re-bands the same input and flag. |
| S6 | should | LP-3 treated priced rate rises as evidence against a premium shock. | LP-3 is withdrawn and its id retired; the discriminator it stood for is the `unknown` row LP-7. |
| S7 | should | A null `turn_watch` can come from a missing 22-day change. | TP-1 reads null only when the series is available, path-qualified and publishes a finite 22-day change. |
| S8 | should | The leadership-crack guard checked a number the owner always writes. | The guard is on clocks: the state is admitted only when its date equals the regime artifact's date from the same run. Rebuilt in revision 3.1 on the regime artifact's embedded copy (§17, C-S2). |
| S9 | should | Six issue tokens were used outside §4's closed list. | §4 lists them, plus `owner_did_not_write`. |
| S10 | should | `unknown` conditions carried no evidence family. | Every row has a family id; A.0 lists the ids. |
| S11 | should | The promised one-line rationale per row was missing. | A.4 carries a rationale column. |
| S12 | should | R-F misdescribed the weekly lane and two step positions. | R-F corrected from `config/dag.yml`. |
| S13 | should | R-D called families "the unit of independence". | R-D calls them groupings that stop the plainest double counting and names the overlaps that remain. §5.3 no longer says "independent". |
| S14 | should | LH-1 and DS-1 said "no absolute damage" where the owner publishes a monitor state. | Both name the owner's monitor and its token; the drawdown numbers are shown as evidence. |
| S15 | should | Refusing any replay on the motivating episodes was partly an evasion. | New slice E1r: one labelled hindsight coverage replay per mapping version (§12, R-I, SH-12). |
| N1 | note | `financial_conditions.state` has no default token. | A.1 corrected: a missing input publishes null. |
| N2 | note | Two different `hy_oas_z` numbers exist. | A.1 and R-C name each. |
| N3 | note | The fed-path sign guard cannot fail on a well-formed artifact. | R-B labels it a corruption check. |
| N4 | note | `usd_dir` was admitted but can never read. | Moved to A.2 until slice E0. |
| N5 | note | The fields behind `possible_missing_as_zero` were never enumerated. | R-B states the scope: none of A.1's "needs" numbers is written through a zero default at the pin; the token applies to the `state` values §7 item 4 lists. |
| N6 | note | The anchoring row did not state its tenors. | A.1 and OD-2 / RI-3 state them. |
| N7 | note | A.6's closing sentence compared paths. | A.6 closes without a cross-path sentence and says its table is a rule check, never page copy. |

## 17. Change log — revision 3.1

The confirmation review of revision 3 re-verified every guard against producer code at the pin
and recomputed the worked example. It found nineteen of the twenty-six earlier findings closed
and seven partly closed, and returned `REQUEST_CHANGES`: one blocking finding, six further
ones and five notes. Every one is accepted.

| # | Severity | Finding | Change |
|---|---|---|---|
| C-B1 | blocker | OD-6 read a categorical classifier as if it were a band. Its `fits` set was the complement of `liquidity`, a negation in disguise; three of its tokens are decided by real-yield and oil inputs while the row sat in the credit family; and in a stress case it alone could decide that family from a real-yield move. | OD-6 is retired. The cause badge is evidence only (A.2), shown beside RI-4 and only when all five of its inputs are published. R-B, R-D, R-H, §7 item 3 and A.6 follow. |
| C-S1 | should | TP-6 authored an equity-breadth side for a rates turn. | TP-6 is an open row reading `unknown`; the breadth component is shown beside the card. |
| C-S2 | should | The leader-damage guard compared two dates that are not equal by construction (last equity close against the regime frame date). | The guard compares the monitor's date with the copy the regime artifact embeds in the same run. |
| C-S3 | should | "Middle token" was not defined mechanically, so the lint had nothing to check. | A.1 carries a Middle column; R-H and the lint read it. The final confirmation pass corrected the turn watch's Middle to its guarded null, so TP-1 passes the lint as written, and tied R-I's wording allowance to the id rule. |
| C-S4 | should | Two body references were stale (§2 row 9, §5.2). | Both corrected: the dollar family is not covered in version 1; the dispersion state is evidence. |
| C-S5 | should | The replay rule allowed changes in either direction, which could become fitting. | R-I is one-directional: a replay may only move a token to `unknown`, tighten a guard or correct wording; dates are closed; all paths and dates are reported; hashes are committed first. |
| C-S6 | should | OD-7's rationale was argued from the pin date. | Rationale restated from the parent's discriminator. |
| C-N1 | note | Condition ids were retired in some places and redefined in others. | R-H states the id rule from this revision on. |
| C-N2 | note | TP-1 reads one tenor where the parent names several. | Rationale says the other tenors are shown in **Now**. |
| C-N3 | note | One producer line reference in R-B was off. | Corrected to RIT:252-253. |
| C-N4 | note | The leader-damage state was shown without how long it had held. | `state_since` is evidence beside the state (A.2, LH-1). |
| C-N5 | note | OD-2's side is authored. | Rationale says so. |

## 18. Change log — revision 3.2

Trigger: PR #8348 (`698f58a0c74b`, slice E0) changed `current_state` in
`engine/rate_inflation_transmission.py`, the decision function behind five A.1 rows. An
independent read-only pass compared every decision function A.1 cites between the version 1
pin and `698f58a0c74b`. `current_state` is the only one whose source differs. Its bands and
middle tokens are unchanged; what changed is what it publishes when an input is missing.
`breakeven_decomposition` moved 41 lines with identical source. No path, condition, reading or
family changed. No projection was built and no replay was run under version 1.

| # | Change | Reason |
|---|---|---|
| V1 | The mapping is `VERDICT_MAPPING_V2`, pinned at `698f58a0c74beff717cd6b69bb728fd7e21581f2`. | R-E: a cited producer rule changed, so the mapping is re-read and re-versioned, not carried. |
| V2 | The five transmission `state` rows list `null` as an owner token. The reader refuses `null` on these rows with the issue `missing`. Their default-word guard stays. | The owner now publishes `null` when its input is missing. A file written before the repair can still carry the old default word, and the guard still refuses it. |
| V3 | `possible_missing_as_zero` applies to no field: the mapping's list is empty. The token stays in the closed issue list. | The eight numbers are `null` when missing. Keeping the issue would mark a genuine 0.00 as possibly missing. |
| V4 | The slice that wires the projection into the builder merges only when the committed `data/transmission/latest.json` on `origin/main` was last written by a commit that descends from `698f58a0c74b`. | A file written before the repair could still carry a zero default, which version 2 would read as a number. |
| V5 | Producer line numbers for the five `state` rows and the two breakeven rows are re-cited at the pin. Every other line number stays at the version 1 pin. | `current_state` grew and the functions below it moved. |
| V6 | R-E names its record, its test and the remedy for a failing pin. A failing pin whose re-read finds no row changed is recorded in the pin file, not re-versioned. | The rule had no operational form. Without one, a failing pin invites a blind hash update, and a re-version for every unrelated edit inside a long producer function would bury the versions that matter. |
| V7 | §2 row 7 (volatility, correlation, positioning) reads `not_covered`. | The family has evidence but no admitted field, and §2's own rule publishes that as `not_covered`. The cell said `partial`. |
| V8 | SH-12 names the mapping version in force when the replay runs. | The registration was written against version 1, and no replay had been run. |

Where Appendix A says "version 1" about a scope decision — what is cited, left open or
retired — the decision is unchanged in version 2.

## 19. Change log — revision 3.3

Trigger: the independent read-only review of the composer (PR #8380, round 2) showed the
module judging a plain date against the cutoff's UTC date while `session_relation` used New
York, and a baseline carry-forward that also fired when `previous` came from a later session.
The contract had not ruled on either. No path, condition, reading or family changed; the
mapping stays `VERDICT_MAPPING_V2`.

| # | Change | Reason |
|---|---|---|
| C1 | §3 clock rule: a plain date stamp is a New York calendar day; `future_dated` and `age_calendar_days` use the New York date of the cutoff; a precision-only stamp change is never "later". | Between 00:00Z and the New York midnight a next-day stamp was read as current, against the information boundary. |
| C2 | §6: a `previous` from a later completed session yields an absent baseline, reason `previous_from_later_session`; carry-forward is only for a same-session rebuild. | The §6 rule allowed carry-forward only within the same session; the composer had carried from a later one. |
| C3 | What-changed classification: a row that moves from `available` to `partial` is judged by the data rules (observation-clock rows: `observation_advanced` / `value_revised` / `owner_verdict_changed` / `clock_only`; snapshot-clock rows: `unattributed` / `clock_only`); when its values, verdict and stamp are all unchanged the status move itself is the new kind `issues_changed`. A row that moves from `stale` or from a non-data status to `partial` is `became_available`. The change-kind list is now ten words. | A partial row still carries its values and verdict, so `became_unavailable` was a label the contract never defined for it; and §3 says statuses are detected, so a pure status move may not vanish from "what changed". |

## Appendix A — `VERDICT_MAPPING_V2`

**Status.** Display tier. Authored by the programme lead on 2026-10-03 from producer code and
committed artifacts at `origin/main` `5f20adbd6be6b136b2efe41585bd4ef964b5bf2e` (the "version 1 pin"),
revised once after independent review (§16), and re-read as version 2 at
`698f58a0c74beff717cd6b69bb728fd7e21581f2` (the "pin") after the producer repair in PR #8348
(§18). Never tested against outcomes. No point-in-time
archive of these owner tokens exists for the motivating episodes (2018–2019, 2022), so the
mapping cannot be replayed on them as evidence. What can be done honestly is narrower and is
required before the page ships: one hindsight coverage replay (slice E1r, rule R-I) that shows
whether each path's conditions can be read at all on those dates. Its output is a check on
wording and guards, not a result. The appendix must be reviewed independently before any code
is written against it, and it changes only by a new version (§5.3).

Abbreviations: RIT `engine/rate_inflation_transmission.py`; YC `engine/yield_curve.py`; YM
`engine/yield_momentum.py`; FX `engine/forex_transmission.py`; TC
`engine/transmission_context.py`; COND `engine/conditions.py`; REG `engine/regime.py`; MS
`engine/market_state.py`; DISP `engine/dispersion.py`; LC `engine/leadership_crack.py`; FP
`engine/fed_path.py`. Line numbers and "at the pin" statements were read at the version 1 pin, except
the five transmission `state` rows and the two breakeven rows of A.1 and the repair citation in
R-B, which are at the pin. Between the two commits every cited producer file except RIT and TC
is byte-identical; `config/dag.yml` was not re-read. Artifacts: T `data/transmission/latest.json`;
R `data/regime/latest.json`; M `data/market_state/latest.json`; D `data/dispersion/regime.json`;
L `data/leadership_crack/latest.json`; B `data/bonds/bond_health.json`.

### A.0 Evidence family ids (closed list for version 1)

With at least one admitted field: `core_pce`, `treasury_curve`, `policy_pricing`, `labour`,
`credit_and_funding`, `participation`, `leader_damage`.

With evidence but no admitted reading: `dispersion`, `dollar`, `oil`, `wages_services`,
`correlation`, `volatility`.

With no audited owner field: `inflation_breadth`, `real_activity`, `earnings`, `positioning`,
`macro_confirmation`, `issuance_and_demand`, `concentration`, `leader_turnover`,
`revision_breadth`.

### A.1 Admitted owner verdicts

"Default" is the token the owner returns when its input is missing — for the five transmission
`state` rows, the word a file written before the repair in PR #8348 carries; since the repair
those rows are `null` when the input is missing — and "needs" is what must be
published and finite beside a token before it is admitted (rule R-B). "Clock" is the date the row
may show; `snapshot` means the artifact's frame date is the only clock, so the row is current
context only (§4 rule 2).

| Field | Tokens | Middle | Class | Owner rule (producer lines) | Clock | Default → needs | Family |
|---|---|---|---|---|---|---|---|
| T `state.inflation.direction` | `re-accelerating`, `cooling`, `steady`, null | `steady` | banded | core PCE 3-month annualised minus 12-month, dead-band ±0.2 pp (RIT:260-262, 266-268, 338) | snapshot | `steady` → `core_pce_3m_ann`, `core_pce_yoy` | `core_pce` |
| T `state.inflation.regime` | `above target`, `at target`, `below target`, null | `at target` | banded | core PCE 12-month above 2.3 / 1.7–2.3 / otherwise (RIT:260, 263-265, 338) | snapshot | `below target` → `core_pce_yoy` | `core_pce` |
| T `state.expectations.anchoring` | `drifting up`, `drifting down`, `anchored`, null | `anchored` | banded | the 5-year-5-year-forward market breakeven minus a 5-year model expectation — two different tenors, and the owner compares them as published — dead-band ±0.3 pp (RIT:271-272, 274-277, 346-347) | snapshot | `anchored` → `market_minus_model_bp` | `treasury_curve` |
| T `state.rates.direction` | `rising`, `falling`, `stable`, null | `stable` | banded | 10-year real yield change over 63 rows, dead-band ±10 bp (RIT:234-235, 239-241, 320) | snapshot | `stable` → `real_10y_chg_63d_bp` | `treasury_curve` |
| T `state.rates.regime` | `restrictive`, `accommodative`, `neutral`, null | `neutral` | banded | 10-year real yield percentile over 1,260 observations, ≥ 0.70 / ≤ 0.30 (RIT:233, 236-238, 319) | snapshot | `neutral` → `real_10y_pctile` | `treasury_curve` |
| T `breakeven_decomp.direction` | `falling`, `rising`, `flat` | `flat` | banded | 10-year breakeven change over 20 rows, dead-band ±8 bp (RIT:442, 463-464, 489, 497) | `breakeven_decomp.as_of` | `flat` → `velocity_bp.chg_20d_bp` | `treasury_curve` |
| T `breakeven_decomp.trend` | `downtrend`, `uptrend`, `choppy`, `n/a` | none (no row reads the field in this version) | composite | RIT:451-462 | `breakeven_decomp.as_of` | `n/a` is the owner's own missing token | `treasury_curve` |
| T `yield_curve.regime.term_premium_dir` | `rising`, `falling`, `stable`, null | `stable` | banded | term-premium estimate change over 63 observations, dead-band ±5 bp; null when the change is missing (YC:522-523) | `yield_curve.asof` | none — the owner publishes null | `treasury_curve` |
| T `yield_momentum.series.<tenor>.turn_watch` (2y, 5y, 10y, 20y, 30y) | `rolldown_forming`, `extreme_high_watch`, `rollup_forming`, `extreme_low_watch`, null | `null`, when guarded (the guard in this row's "Default → needs" column; otherwise `unknown`) | composite | YM:159-182, 274-275, 297-300. Null is also returned when the 22-day change is missing or fewer than 60 values exist (YM:166) | the series' own `as_of` | null → `status: available`, `path_qualified: true` and a finite `velocity_bp.22d`; otherwise `unknown` | `treasury_curve` |
| R `conditions.labor_nowcast.read` | `labor cooling`, `labor firm`, `labor mixed` | `labor mixed` | composite | two or more of three "cooling" votes, else two or more of three "firm" votes, else `labor mixed` (COND:738-748). Cooling votes: jobless claims year on year ≥ +10%; job postings 3-month change ≤ −5%; withheld tax year on year below 0. Firm votes: claims ≤ 0; postings ≥ 0; withheld tax ≥ +2.0%. Three of the six cuts sit at zero, but every leg has a dead zone between its two votes, so no single zero-crossing moves the read from one side to the other | snapshot (the block has no clock of its own) | `labor mixed` → `claims_yoy_pct`, `indeed_chg_3m_pct`, `withheld_tax_yoy_pct` | `labour` |
| R `conditions.financial_conditions.state` | `loose`, `neutral`, `tight`, null | `neutral` | banded | NFCI level, dead-band ±0.10; null when NFCI is missing (COND:535-538, 622) | `conditions.vintages.nfci` | none — the owner publishes null | `credit_and_funding` |
| R `conditions.complacency.breadth_div` | true, false | none | banded | index within 3% of its high (`spy_high_prox` ≥ 0.97) while the share of stocks above their 200-day average is below the 40th percentile of its own history (COND:973-974) | `conditions.vintages.pct_above_200` | false → `spy_high_prox`, `breadth_above200_pctile` | `participation` |
| R `liquidity_quality.label` | `benign-expansion`, `stress-expansion`, `neutral`, `neutral-hollow`, `contracting`, `unknown` | none (no row reads the field in this version) | composite | quantity change crossed with the stress overlay and the reverse-repo floor (REG:111-124, 127; floor `config.yml` `rrp_floor_bn`) | `liquidity_quality.asof` | `unknown` is the owner's own missing token | `credit_and_funding` |
| R `liquidity_quality.stress_overlay.confirming_stress` | true, false | none | composite, guarded (R-C) | true when the z-score of the 20-day change in the high-yield spread is ≥ 1.0 (`config.yml` `stress_oas_z`), **or** NFCI is above zero and its 20-day change is positive — a bare sign (REG:183-202). The overlay's `hy_oas_z` is the z of the 20-day change; it is not the co-state `hy_oas_z`, which is the z of the level (2.78 against 0.95 at the pin) | inherited from `liquidity_quality.asof` and labelled as inherited | false → R-C | `credit_and_funding` |
| M `components[key=breadth].tone` | `good`, `warn`, `bad` | `warn` | composite | band over the component's score, ≥ 0.60 / ≥ 0.42 (MS:100-105). The score is the percentile of the share of stocks above their 200-day average, minus 0.16 when `breadth_div` is true (MS:317-321); the component is absent when the percentile is missing | `input_vintages.pct_above_200` | none — but admitted only when `degraded` is false | `participation` |
| L `state` | `INTACT`, `CRACKING`, `BROKEN` | none (`CRACKING` is a named state, not a dead band) | banded with hysteresis | LC:40-58, 237-288. The cohort is fixed: `ai_semiconductors`, `ai_infra`, `memory_storage`, `semicap_equipment` — never "all current leaders". The owner writes nothing when fewer than three members are fresh (LC:319-323), leaving the previous file in place | `asof` | every token → R's embedded `leadership_crack` (written by the same `engine_run`, `engine/run.py:993`) is non-null and its `asof` equals L's `asof`; otherwise status `stale`, issue `owner_did_not_write`. L's `asof` is its last equity-close date (LC:342), not the regime frame date, so equality with R's top-level `asof` would not prove the same run | `leader_damage` |
| B `fed_path.implied_cuts_12m` | integer | `0` | banded | priced path rounded to quarter-points (FP:32, 132, 155-158). Read as: ≥ 1 cuts priced; ≤ −1 rises priced; 0 no change priced | `fed_path.asof` | none — plus the corruption check in R-B | `policy_pricing` |

Evidence shown in **Now** from admitted fields that carry no path condition in version 1:
`state.rates.regime`, `breakeven_decomp.trend`, `liquidity_quality.label` and its
`rrp_exhausted` flag, and the non-10-year `turn_watch` tenors.

### A.2 Evidence only — shown with its number, reading `unknown`

| Field | Why |
|---|---|
| T `breakeven_decomp.cause_badge.cause` | a categorical classifier, not a band (`_classify_cause`, RIT:356-388). For a falling breakeven: `liquidity` (credit-spread level z ≥ 1.0 and volatility percentile ≥ 0.80 and nominal yields falling), else `real_rate` (real yield up ≥ 10 bp with oil within ±5%), else `oil` (oil ≤ −8%), else `growth` — a residual, not a measured growth read. Rising → always `reflation`; otherwise `quiet`. Three of its tokens are decided by real-yield and oil inputs and one by credit and volatility inputs, so no evidence family holds it, and a row reading "not `liquidity`" would fit almost every fall. Shown beside RI-4 as the owner's attribution with its five co-state numbers (`oil_chg_20d_pct`, `real10y_chg_20d_bp`, `nom10y_chg_20d_bp`, `hy_oas_z`, `vix_pctile`), and displayed only when all five are finite, because a missing input falls through to a later token |
| T `dollar_channel.usd_dir` | banded by the owner (broad dollar rate of change over 63 observations, dead-band ±0.5%, FX:154-160), but the number it was decided from is never published (`roc_pct` is null at the pin, TC:222) and the block's date is the newest of several pairs, not this field's. Admitted when slice E0 publishes both |
| D `state` | a level tercile of dispersion (percentile ≥ 0.66 / ≤ 0.33 against the whole supplied panel, whose length is not published; DISP:26, 162-186). No path condition reads a level; the discriminator is a change (A.4, GB-2) |
| D `avg_corr` | a number — a variance-ratio proxy over the last 63 rows, not a measured correlation (§10) |
| R `labor_nowcast.claims_trend`, `indeed_trend`, `income_trend` | two tokens split at zero; a zero change reads "falling" (`sign_only_verdict`) |
| R `financial_conditions.trend` | two tokens split at zero on the 13-week change |
| R `complacency.state` | one of its legs is the bare sign of a 21-day credit-spread change, which alone can move the state (`contains_sign_only_leg`); cite `breadth_div` instead |
| R `stress_overlay.nfci_trend` | two tokens split at zero |
| R `stress_overlay.hy_oas_pct` | the spread level, a number with no owner verdict (`no_owner_verdict`) |
| M `components[key=vol].tone` | the component blends in `complacency.state` (`contains_sign_only_leg`) |
| M any component's `arrow` or `read_en` | `arrow` uses different bands from `tone`; `read_en` is prose |
| L `med_dd`, `carnage_share_ema`, `share10`, `share30`, `state_since` | the numbers behind the monitor's state and the date it entered that state, shown beside it so a reader sees how long the state has held |
| `data/regime/regime_one.json` `macro.quad`, `tape.quad` | sign of a composite; `macro.growth` is a number whose legs have unequal freshness |
| T `yield_curve.regime.key` | bare signs of a 21-observation change |
| `data/commodity/latest.json` `assets.oil.trend`; `data/commodity/complex_latest.json` `dollar_dir` | bare signs |
| R `theme_revisions[].broadening_state`, `level_state` | sign rules, per theme, no market-level verdict |
| every published number without an owner token | `no_owner_verdict` |

### A.3 Not cited in version 1

| Field | Why |
|---|---|
| T `state.rates.turn_watch` | a different vocabulary under the same key name as the per-tenor field (§7, defect 6) |
| B `fed_path.gap.lean_en` | a label string |
| `data/commodity/shock_state.json` | no producer step found for this path; its newest entry is dated 2026-09-18 |
| `data/commodity/complex_latest.json` `complex_regime` | a lagged label that contradicts the same file's `dollar_dir` at the pin |
| `data/rates_command/latest.json` `board.policy_row.state`, `rate_path_row` | vocabulary not audited; `rate_path_row` is an older copy of `fed_path` (2026-10-01, 82 bp against the owner's 2026-10-02, 83 bp) |
| `site/basketdata/breadth_split.json` | the stance is published only as text and its builder is not in `config/dag.yml` |
| `site/basketdata/vol_weather.json` | vocabulary not audited from producer code |
| `data/neuralweb/world_state.json` `factor_weather` | its producer runs after `build_rates_command` (`config/dag.yml:1601` against `:1557`) |
| T `dollar_channel` prose and scenario fields | free text |

### A.4 Conditions per path

One row per condition: the statement the page shows, the one owner field it reads, which of
that owner's tokens are the side the statement names (`fits`), the opposite side
(`does_not_fit`) or the owner's middle (`not_discriminating`), the evidence family, and why the
row is there. Rule R-H governs every row.

A discriminator the parent architecture names but for which no owner field is admitted is listed
as an open row: it carries a family, reads `unknown` with its reason, and authors no token
mapping. Where the parent states a side ("dispersion falling without correlation rising") the
row quotes it; where it does not ("dollar behaviour") the row names the discriminator only, and
no side is authored until a field is admitted, which is a new mapping version.

**`orderly_disinflation`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| OD-1 | The recent pace of core inflation is below its 12-month pace | T `state.inflation.direction` | `cooling` | `re-accelerating` | `steady` | `core_pce` | "Inflation pressure eases" is this owner's own comparison |
| OD-2 | Market-implied inflation expectations are drifting down against the model estimate (5-year-5-year-forward breakeven against a 5-year model) | T `state.expectations.anchoring` | `drifting down` | `drifting up` | `anchored` | `treasury_curve` | The parent names expectations without a side; reading `drifting down` as the side that fits is this mapping's authored choice (RI-3 is its mirror). `anchored` is the owner's dead-band and says nothing either way |
| OD-3 | The labour read is firm | R `labor_nowcast.read` | `labor firm` | `labor cooling` | `labor mixed` | `labour` | "Without broad deterioration in labour" |
| OD-4 | The owner's credit-stress flag is off | R `stress_overlay.confirming_stress` | false | true | — (a flag has no middle) | `credit_and_funding` | "Without broad deterioration in credit"; guarded by R-C |
| OD-5 | Financial conditions are loose | R `financial_conditions.state` | `loose` | `tight` | `neutral` | `credit_and_funding` | Same clause; the level band, not the change |
| OD-7 | Real yields are falling | T `state.rates.direction` | `falling` | `rising` | `stable` | `treasury_curve` | The parent's "real-rate velocity". Inflation pressure that eases in an orderly way is read with real yields easing alongside it; rising real yields are the opposite side. Identical to GD-1 |
| OD-8 | Inflation composition | none | — | — | `unknown`: `no_admitted_owner_field` | `inflation_breadth` | Named by the parent; no owner verdict audited |

`OD-6` is retired and never reused.

**`growth_deterioration`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| GD-1 | Real yields are falling | T `state.rates.direction` | `falling` | `rising` | `stable` | `treasury_curve` | "Lower yield pressure"; identical to OD-7 by R-H |
| GD-2 | The labour read is cooling | R `labor_nowcast.read` | `labor cooling` | `labor firm` | `labor mixed` | `labour` | "Weakening activity"; mirror of OD-3 |
| GD-3 | The owner's credit-stress flag is on | R `stress_overlay.confirming_stress` | true | false | — | `credit_and_funding` | "Weakening financing conditions"; mirror of OD-4; guarded by R-C |
| GD-4 | Financial conditions are tight | R `financial_conditions.state` | `tight` | `loose` | `neutral` | `credit_and_funding` | Mirror of OD-5 |
| GD-5 | Real activity is weakening | none | — | — | `unknown`: `no_admitted_owner_field` | `real_activity` | The one composite that exists has legs of unequal freshness (A.2) |
| GD-6 | Earnings context | none | — | — | `unknown`: `no_admitted_owner_field` | `earnings` | Per-theme sign rules only; no market-level verdict |
| GD-7 | Dollar behaviour | T `dollar_channel.usd_dir` (A.2) | — | — | `unknown`: status `unknown_date` | `dollar` | Readable once slice E0 publishes the number and its date; no side authored |
| GD-8 | Credit spreads are wide in level | R `stress_overlay.hy_oas_pct` (A.2) | — | — | `unknown`: `no_owner_verdict` | `credit_and_funding` | The owner bands the change in spreads, not their level |

**`renewed_inflation_pressure`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| RI-1 | The recent pace of core inflation is above its 12-month pace | T `state.inflation.direction` | `re-accelerating` | `cooling` | `steady` | `core_pce` | Mirror of OD-1 |
| RI-2 | Core inflation is above the owner's 1.7–2.3% band | T `state.inflation.regime` | `above target` | `below target` | `at target` | `core_pce` | "Persists"; the band is the owner's, not a policy statement |
| RI-3 | Market-implied inflation expectations are drifting up against the model estimate (same tenors as OD-2) | T `state.expectations.anchoring` | `drifting up` | `drifting down` | `anchored` | `treasury_curve` | Mirror of OD-2 |
| RI-4 | Breakevens are rising | T `breakeven_decomp.direction` | `rising` | `falling` | `flat` | `treasury_curve` | The parent's "breakevens (with liquidity caveats)"; the caveat is shown beside it from the cause badge (A.2) |
| RI-5 | Wage and services inflation are firming | none (numbers only) | — | — | `unknown`: `no_owner_verdict` | `wages_services` | Numbers are published; no owner token |
| RI-6 | The market prices rate rises over the next 12 months | B `fed_path.implied_cuts_12m` | ≤ −1 | ≥ 1 | 0 | `policy_pricing` | The parent's "policy repricing" |
| RI-7 | Inflation is broadening across components | none | — | — | `unknown`: `no_admitted_owner_field` | `inflation_breadth` | "Broadens … rather than a single transitory print" |
| RI-8 | Oil mechanism | `data/commodity/latest.json` `assets.oil.trend` (A.2) | — | — | `unknown`: `sign_only_verdict` | `oil` | The only owner token is a bare sign |

**`long_end_premium_shock`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| LP-1 | The term-premium estimate is rising | T `yield_curve.regime.term_premium_dir` | `rising` | `falling` | `stable` | `treasury_curve` | One model's estimate; LP-6 says agreement between models is unread |
| LP-2 | Real yields are rising | T `state.rates.direction` | `rising` | `falling` | `stable` | `treasury_curve` | Mirror of OD-7 and GD-1 |
| LP-4 | The curve is steepening from the long end | T `yield_curve.regime.key` (A.2) | — | — | `unknown`: `sign_only_verdict` | `treasury_curve` | Bare signs of a 21-observation change |
| LP-5 | Issuance and demand at the long end are deteriorating | none | — | — | `unknown`: `no_admitted_owner_field` | `issuance_and_demand` | Named by the parent; no owner |
| LP-6 | Term-premium models agree | none | — | — | `unknown`: `no_admitted_owner_field` | `treasury_curve` | One estimate is published; cross-model disagreement is not measured |
| LP-7 | The rise in long-end yields is not explained by the priced policy path | none | — | — | `unknown`: `no_owner_verdict` | `policy_pricing` | The path's defining claim. No owner decomposes it, and the direction of priced policy alone is not evidence either way |

`LP-3` is retired and never reused.

**`technical_pause`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| TP-1 | The owner flags a turn forming in the 10-year yield | T `yield_momentum.series.10y.turn_watch` | `rolldown_forming`, `rollup_forming` | `extreme_high_watch`, `extreme_low_watch` | null, when guarded (A.1) | `treasury_curve` | "A reversal is visible". The owner's extreme tokens mean stretched and not turning — the opposite; null means it flags nothing. The parent names "multi-horizon yield turns"; the other tenors' flags are shown in **Now**, not read into the card |
| TP-4 | Positioning is stretched | none | — | — | `unknown`: `no_admitted_owner_field` | `positioning` | Named by the parent; no owner |
| TP-5 | Later macro data have not confirmed the move | none | — | — | `unknown`: `no_admitted_owner_field` | `macro_confirmation` | The path's defining claim; no owner verdict. Inflation and labour evidence is shown beside the card, not read into it: which side confirms depends on the direction of the turn |
| TP-6 | Market breadth confirms the turn | none (M `components[breadth].tone` is shown beside the card, not read into it) | — | — | `unknown`: `no_admitted_owner_field` | `participation` | Named by the parent without a side. Which side confirms depends on the direction of the turn, as for TP-5; an equity-breadth side for a rates turn would be authored |

`TP-2` and `TP-3` are retired and never reused.

**`continued_selective_concentration`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| SC-1 | The index is within 3% of its high while the share of stocks above their 200-day average is in the lower 40% of its own history | R `complacency.breadth_div` | true | false | — | `participation` | "Index strength carried by a narrow group", in the owner's exact construction |
| SC-2 | The owner's credit-stress flag is off | R `stress_overlay.confirming_stress` | false | true | — | `credit_and_funding` | "Credit and funding stability"; identical to OD-4 |
| SC-3 | Financial conditions are loose | R `financial_conditions.state` | `loose` | `tight` | `neutral` | `credit_and_funding` | Identical to OD-5 |
| SC-4 | Cap-weighted returns are ahead of equal-weighted | none | — | — | `unknown`: `no_admitted_owner_field` | `concentration` | Named by the parent; no owner on `origin/main` |
| SC-5 | The same leaders persist | none | — | — | `unknown`: `no_admitted_owner_field` | `leader_turnover` | Named by the parent; no owner |

**`genuine_broadening`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| GB-1 | The breadth component reads strong | M `components[breadth].tone` | `good` | `bad` | `warn` | `participation` | "Participation widens". It re-bands SC-1's input and subtracts for SC-1's flag (when the flag is true the tone is `bad` by construction), so the two are one family and never two confirmations |
| GB-2 | Dispersion is falling without correlation rising | none (D `state` and `avg_corr` are evidence, A.2) | — | — | `unknown`: `no_owner_verdict` | `dispersion` | The owner publishes a level tercile and a proxy number; neither is the change the parent names |
| GB-3 | Revision breadth is widening | none | — | — | `unknown`: `no_admitted_owner_field` | `revision_breadth` | "With fundamental support"; per-theme sign rules only |
| GB-4 | Participation is rising on a fixed historical universe | none | — | — | `unknown`: `no_admitted_owner_field` | `participation` | Needs historical membership (slice D1) |

**`internal_leadership_handoff`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| LH-1 | The owner's leader-damage monitor for the tracked AI-hardware cohort reads intact | L `state` | `INTACT` | `CRACKING`, `BROKEN` | — | `leader_damage` | "No absolute damage to the cohort", limited to the cohort and monitor that exist; the drawdown numbers and the date the state was entered (`state_since`) are shown beside it |
| LH-2 | Leaders are turning over inside a theme | none | — | — | `unknown`: `no_admitted_owner_field` | `leader_turnover` | The path's defining claim; no owner |
| LH-3 | Theme-level participation is holding | none | — | — | `unknown`: `no_admitted_owner_field` | `participation` | No theme-level participation verdict |

**`deterioration_spreading_to_leaders`**

| Id | Statement | Field | fits | does_not_fit | not_discriminating | Family | Why this row |
|---|---|---|---|---|---|---|---|
| DS-1 | The owner's leader-damage monitor for the tracked AI-hardware cohort reads cracking or broken | L `state` | `CRACKING`, `BROKEN` | `INTACT` | — | `leader_damage` | Mirror of LH-1 |
| DS-2 | The owner's credit-stress flag is on | R `stress_overlay.confirming_stress` | true | false | — | `credit_and_funding` | Identical to GD-3 |
| DS-3 | Financial conditions are tight | R `financial_conditions.state` | `tight` | `loose` | `neutral` | `credit_and_funding` | Identical to GD-4 |
| DS-4 | Correlation is rising together with dispersion | none admitted (`vol_weather`, A.3) | — | — | `unknown`: `vocabulary_not_audited` | `correlation` | Named by the parent |
| DS-5 | Funding and credit are worsening | R `financial_conditions.trend`, `stress_overlay.nfci_trend` (A.2) | — | — | `unknown`: `sign_only_verdict` | `credit_and_funding` | "Worsening" is a change; the owner's change tokens are bare signs. DS-2 and DS-3 read levels and a flag |

### A.5 Rules

- **R-A — admission by class.** Only `banded` and `composite` tokens yield a reading (§5.3).
- **R-B — missing-input guards.** A token is admitted only when the numbers A.1 lists under
  "needs" are published and finite beside it; otherwise the reading is `unknown` with the issue
  `owner_default_on_missing`. For most fields this binds only the default token, because a
  missing input can produce no other. One field is bound on every token, because its owner
  can leave a previous file in place: the leader-damage state (the same-run check in A.1). In version 1 `possible_missing_as_zero` applied to the eight
  `state` numbers the owner wrote through a zero default (RIT:268-271, 289-293 at the version 1 pin):
  `rates.nominal_10y`, `rates.curve_2s10s`, `rates.curve_tp_adj`, `rates.policy_gap`,
  `inflation.core_cpi_yoy`, `inflation.headline_cpi_yoy`, `inflation.ppi_core_yoy` and
  `inflation.eci_comp_yoy`. None of A.1's "needs" numbers is among them. The repair in PR #8348
  publishes `null` for the eight when the observation is missing (RIT:224-230, 321-324,
  332-336), so in version 2 the list is empty and a published 0.00 is a reading; the rule-pin
  test (R-E) fails if the owner's rule changes again. Before the repair the owner's
  inflation `regime` compared `(core_pce_yoy or 0) > 2.3`, which is why the default word a
  pre-repair file carries is `below target`; the owner now publishes `null` instead
  (RIT:263-265). One corruption check: `fed_path.implied_cuts_12m` is read
  only when `implied_cuts_12m × implied_bp_12m ≤ 0`. The owner derives both from one number
  with opposite signs (FP:131-132), so a well-formed artifact always passes; a failure means the
  file is damaged, and reads `unknown`, issue `owner_sign_inconsistent`. The projection never
  cites the Rates Command copy of the path beside the owner.
- **R-C — the credit-stress flag.** The owner sets `confirming_stress` true when the z-score of
  the 20-day change in the high-yield spread is at least 1.0, **or** when NFCI is above zero and
  its 20-day change is positive. The second leg ends in a bare sign. The projection therefore
  admits:
  - `true` only when the published overlay `hy_oas_z` is above 1.00, or the published `nfci` is
    below zero. Either proves the banded credit leg fired — the first directly, the second
    because the other leg requires NFCI above zero.
  - `false` only when the overlay `hy_oas_z` is published and finite and the published `nfci` is
    below zero. Then the credit leg was measured and did not fire, and the other leg could not.
  - Anything else is `unknown`: issue `contains_sign_only_leg` when the numbers are published
    (the flag may rest on the bare sign), `owner_default_on_missing` when they are not (`false`
    is also what the owner returns with no inputs).
  The comparisons are strict so that rounding in the published numbers cannot admit a case the
  owner's own rule would not. Composites whose sign leg cannot be excluded from published numbers
  are evidence only (A.2).
- **R-D — family roll-up inside one path.** For each evidence family among a path's conditions,
  ignore members reading `unknown` or `not_discriminating`. If the rest agree, the family takes
  that reading. If they split between `fits` and `does_not_fit`, the family reads `mixed`. If
  none remain, the family reads `not_discriminating` when any member did, else `unknown`.
  Families are groupings that stop the plainest double counting. They are **not** independent
  witnesses, and the page never calls them independent. Overlaps that remain across families: priced policy and the Treasury curve are set by the same market;
  NFCI itself includes credit and equity-volatility measures; the leader cohort is part of the
  universe the breadth inputs count. Within a family: nominal yield,
  real yield, breakeven and term premium are one (`treasury_curve`); the two core-PCE verdicts
  are one (`core_pce`); the stress flag, financial conditions and liquidity quality
  are one (`credit_and_funding`); the breadth divergence and the breadth component are
  one (`participation`), the second being a re-banding of the first's inputs.
- **R-E — rule pins.** Slice E1 ships a test that hashes the source of every producer decision
  function cited in A.1 and the configured thresholds they read. A producer rule change fails
  the test; the mapping is then re-reviewed and re-versioned, never silently carried.
  Operational form (revision 3.2): `config/regime_outlook_rule_pins.json` names the mapping
  version and the pin, and lists each function (file, name, the sha256 of its source text, the
  fields it decides) and each configured value. `tests/test_rates_command_outlook_rule_pins.py`
  recomputes them from the files without importing the producers. When it fails, the rows that
  cite the changed function are re-read against the new source. If a row's tokens, bands,
  middle, default or guard assumption changed, the mapping takes a new version. If none did,
  the pin is updated and the re-read is recorded in the pin file's `reviews` list (date,
  commit, functions, finding). A pin is never updated without that record.
- **R-F — build order.** Positions at the version 1 pin (`config/dag.yml`): R and L are written by
  `engine_run` (:624; L from `engine/run.py:987-993`); M by `scripts.build_site`
  (`market_state.persist`, :683; declared at :3917-3936); D by `build_dispersion_regime`
  (:726); B by `scripts.build_bonds` and T by `scripts.build_transmission` (members :874 and
  :876 of the cluster `cl_markets`, node `band` :865) — all before `build_rates_command`
  (:1557). The weekly lane runs `engine_run` (:3200), `build_site` (:3207), `build_bonds`
  (:3232) and `build_transmission` (:3236) before `build_rates_command` (:3262). It does not
  run `build_dispersion_regime`; there D is the last committed file and its own clock says so
  (§2).
- **R-G — clocks.** A `snapshot` row may yield a reading as current context. It is never the
  basis of a "what changed", history or transition statement (§4 rule 2).
- **R-H — one convention for every row.** A condition is a positive statement that names one
  side of one owner's band, or the on or off state of one owner's flag. `fits` is that side;
  `does_not_fit` is the opposite side; `not_discriminating` is exactly the token A.1's Middle
  column names for the field, in every row that reads it. A field whose Middle is "none" has
  no `not_discriminating` column, and an intermediate named state (`CRACKING`) is a side, not a
  middle. Negated statements ("is not cooling") are not used,
  because a negation moves the middle token into `fits`. Two rows with the same statement are
  the same row — same field, same three columns — wherever they appear; a statement and its
  opposite have mirrored `fits` and `does_not_fit` and the same middle. For an owner whose
  tokens are not one axis (the turn watch), exactly one row reads the field in
  this version and its rationale places every token. Slice E1 ships a lint test over the
  machine form of A.4: for every field read by more than one row, the rows are identical or
  exact mirrors; no row that reads a field states the negation of an owner token; every row
  carries a family from A.0 and a rationale; every `not_discriminating` token is the field's
  Middle. Ids: once this revision is on `origin/main`, a condition id is never redefined — a
  changed statement or side takes a new id and the old one is retired. Ids changed before that
  point are listed in §15 to §17.
- **R-I — coverage replay (slice E1r).** Once per mapping version, the owner decision functions
  cited in A.1 are run on today's stored frames truncated to four dates fixed here before
  anything is looked at: 2018-10-31, 2019-08-30, 2022-06-30 and 2022-10-31. The output per
  date and path is the list of condition readings, labelled on its face: *hindsight
  reconstruction on revised data; not point-in-time; not evidence of skill*. It answers one
  question — can each condition be read at all, and does any guard or wording misfire — and a
  change it prompts, in a new version that says so, may only correct the wording of a
  statement or rationale without changing its field, token columns, side or family (a changed
  statement takes a new id under R-H), move a token to `unknown`, or tighten a guard. It may never move a token into
  `fits` or `does_not_fit`, add or remove a row, or change a statement's side or a row's
  family. All nine paths and all four dates are reported, none omitted. The frame hashes and
  the truncation rule are committed with the output before any change is proposed. The SH-12
  dates are closed: a later replay uses the same four dates, or new dates registered as a new
  seen-history row before it runs. It may never be used to make a path fit an episode, to choose between paths, or as support for
  any claim on the page. The dates enter the seen-history register as SH-12 (§9). Fields with
  no stored history are reported `unknown: insufficient_history`, not approximated.

### A.6 Worked example at the pin (2026-10-02 artifacts)

A check that the rules can be applied by hand. It is not page copy and not a market view.

| Path | Condition readings | Family roll-up |
|---|---|---|
| `orderly_disinflation` | OD-1 fits (`cooling`; 2.05 against 3.01); OD-2 not_discriminating (`anchored`; −23 bp published); OD-3 fits (`labor firm`); OD-4 does_not_fit (true; overlay `hy_oas_z` 2.78 > 1.00, admitted); OD-5 fits (`loose`; NFCI −0.548); OD-7 does_not_fit (`rising`; +58 bp); OD-8 unknown | `core_pce` fits; `treasury_curve` does_not_fit; `labour` fits; `credit_and_funding` mixed; `inflation_breadth` unknown |
| `growth_deterioration` | GD-1 does_not_fit (`rising`); GD-2 does_not_fit (`labor firm`); GD-3 fits (true); GD-4 does_not_fit (`loose`); GD-5 to GD-8 unknown | `treasury_curve` does_not_fit; `labour` does_not_fit; `credit_and_funding` mixed; `real_activity`, `earnings`, `dollar` unknown |
| `renewed_inflation_pressure` | RI-1 does_not_fit (`cooling`); RI-2 fits (`above target`; 3.01); RI-3 not_discriminating (`anchored`); RI-4 not_discriminating (`flat`; default token, +1 bp published); RI-5 unknown; RI-6 fits (−3; corruption check holds: −3 × 83 ≤ 0); RI-7, RI-8 unknown | `core_pce` mixed; `treasury_curve` not_discriminating; `policy_pricing` fits; `wages_services`, `inflation_breadth`, `oil` unknown |
| `long_end_premium_shock` | LP-1 fits (`rising`; +27 bp); LP-2 fits (`rising`); LP-4 to LP-7 unknown | `treasury_curve` fits; `issuance_and_demand`, `policy_pricing` unknown |
| `technical_pause` | TP-1 does_not_fit (`extreme_high_watch`; series available, qualified, 22-day change +45 bp); TP-4, TP-5, TP-6 unknown | `treasury_curve` does_not_fit; `participation`, `positioning`, `macro_confirmation` unknown |
| `continued_selective_concentration` | SC-1 fits (true; 0.992 and 0.055 published); SC-2 does_not_fit (true); SC-3 fits (`loose`); SC-4, SC-5 unknown | `participation` fits; `credit_and_funding` mixed; `concentration`, `leader_turnover` unknown |
| `genuine_broadening` | GB-1 does_not_fit (`bad`); GB-2 to GB-4 unknown | `participation` does_not_fit; `dispersion`, `revision_breadth` unknown |
| `internal_leadership_handoff` | LH-1 fits (`INTACT`; R's embedded copy dated 2026-10-02, equal to L's `asof`; state entered 2026-10-02); LH-2, LH-3 unknown | `leader_damage` fits; `leader_turnover`, `participation` unknown |
| `deterioration_spreading_to_leaders` | DS-1 does_not_fit (`INTACT`); DS-2 fits (true); DS-3 does_not_fit (`loose`); DS-4, DS-5 unknown | `leader_damage` does_not_fit; `credit_and_funding` mixed; `correlation` unknown |

What the example shows about the mapping's limits on this date: every card has at least one
family that cannot be read; the credit-and-funding family reads `mixed` in every card that
reads it, because the owner's stress flag is on while its conditions level is loose; and every
market-structure card lacks an owner for the discriminators that define it (cap-weight against
equal-weight, leader turnover, revision breadth, correlation). That is the honest output.
Nothing in the table says which path is occurring, and no sentence comparing one card with
another may be written from it.
