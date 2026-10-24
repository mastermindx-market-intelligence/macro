# C19 WP31 — Incremental information of the source-backed issuer answer (PREREGISTRATION)

**Registered:** 2026-10-17, Commission 19 (Data Intelligence), work package WP31 (MAS-281).
**Scope:** whether the source-backed issuer answer, read at the last market close before an
issuer's quarterly earnings release, carries information about the direction of that
quarter's year-over-year diluted-EPS change beyond a persistence baseline.
**Status:** frozen design only. No evaluator, no data read, no label read. Everything above the
§10 amendments heading is frozen at merge; amendments append below it, prospectively only.

---

## §0 Honest framing — read first

- **Zero authority.** Nothing here changes a rank, a size, a gate, a display tier, or the
  integrated-answer composer's enablement. No ranker, sizer, or user surface consumes the
  result. `MACRO_INTEGRATED_ANSWER_ENABLED` stays unset.
- **A PASS buys a REVIEW, never authority.** The best possible outcome is a written
  adjudication request; promotion of anything would need its own gauntlet under the
  promotion-gate law.
- **Prospective only, no backfill.** Every episode whose release time precedes the merge of
  this document is EXPOSED and is excluded from every reported statistic. Exposed episodes
  may be used only to smoke-test plumbing, labelled `EXPOSED`, never counted.
- **The sample is small and slow.** Five issuers report about four times a year; fiscal-Q4
  labels are often structurally unavailable (§3.3). Expect roughly fifteen evaluable
  episodes a year and an `INCONCLUSIVE` verdict for at least two years. That is the honest
  expected outcome, not a failure of the study. More agents cannot accelerate it.
- **Null, inconclusive and adverse results are reported with the same prominence as a
  pass.** Every arm, contrast and `NOT_EVALUABLE` count in §6 is printed on every read.
- **No language model sits in any arm.** All arms are deterministic rules over stored
  source records, so historical-knowledge contamination of a model cannot leak into a
  forecast. An amendment that adds a model-backed arm must exclude every episode before
  that model's knowledge cutoff for that arm.

## §1 Question, unit, universe

**Question.** On prospective episodes, does the composed, source-backed answer (arm A2)
call the sign of the year-over-year change in quarterly diluted EPS more often than the
same answer with the expectation source family removed (arm A2[−K], which reduces to
persistence)? Equivalently: what does the expectation source add, inside the composed
answer, over SEC-reported history alone?

**Unit (episode).** `e = (issuer, fiscal quarter q)`, defined by the first SEC filing on
Form 8-K carrying the issuer's earnings release for `q` as Exhibit 99.1. Its release time
`t_rel(e)` is that filing's EDGAR acceptance timestamp (converted to UTC).

**Universe (frozen).** The five issuers of `production_registry()` in
`engine/company_intelligence/event_workspace.py` at the registration commit:

| Issuer | Driver family (cluster key) | Fiscal year end month |
|---|---|---|
| AAPL | `AAPL` | 9 |
| DHI | `HOMEBUILDERS` | 9 |
| PHM | `HOMEBUILDERS` | 12 |
| KBH | `HOMEBUILDERS` | 11 |
| TOL | `HOMEBUILDERS` | 10 |

An issuer added to or removed from that registry later does not change this universe;
adding one is an amendment (§10) and its episodes count only after the amendment merges.

**Eligibility.** `t_rel(e)` is strictly after the committer time of `PREREG_COMMIT` (§8).

## §2 Temporal view and leakage rules

**Cutoff.** `C(e)` = the scheduled close (regular or early close, NYSE calendar) of the
last NYSE session that ends strictly before `t_rel(e)`.

Leakage rules, each fail-closed:

1. **Point-in-time reads only.** Every feature input is read as it existed at `C(e)`:
   expectation records with `system_observed_at <= C(e)`; event-workspace versions with
   `generated_at <= C(e)`; SEC filings with EDGAR acceptance `<= C(e)`. A record observed
   after `C(e)` is never a feature input, including corrections whose stated effective
   time precedes `C(e)`.
2. **The q release is never a feature.** The workspace generated from the `q` release is
   after `C(e)` by construction; the composed answer's SEC leg reads the `q−1` release.
3. **Unrecoverable history is not guessed.** If the version that existed at `C(e)` cannot
   be recovered (overwritten without history), the affected arm is
   `NOT_EVALUABLE(pit_unrecoverable)` for that episode — never filled with a later version.
4. **Pre-cutoff disclosure.** If any public release of `q` results is known to precede
   `C(e)`, the episode is `NOT_EVALUABLE(pre_cutoff_leak)`.
5. **Silent partials count.** A leg that is absent, stale, zero-row, or reports success
   with a missing component is `ABSTAIN` or `NOT_EVALUABLE` with a named reason — never a
   silent drop. (This covers the composer's latent silent-partial path on the
   earnings-expectation leg found in the C19 WP22 census.)

## §3 Sources, features, label

### §3.1 Expectation family `K` (Yahoo Finance via the k3e capture)

Source: `data/revisions/expectation_observations.parquet` and
`data/revisions/expectation_attempts.parquet`, written nightly by the existing collector
(`collectors/equity_revisions.py`) and read through `inspect_expectation_surface`
(`engine/k3e_expectation_surface.py`). Selection for episode `e`:

- `metric = "EPS"`, `horizon_label_raw = "0q"` (the provider's relative current-quarter
  label), provider `yfinance`, record class `earnings_estimate`.
- The newest capture group (one `provider_payload_hash`) with `system_observed_at <= C(e)`.
- Because `"0q"` is relative, the group's `period_end` must identify quarter `q` (within
  7 calendar days of `q`'s period end); a null or different `period_end` is
  `ABSTAIN(period_mismatch)`.
- Values `average` and `year_ago` (observation types of `ESTIMATE_TYPES`) from that one group.

### §3.2 SEC family `S`

- **Reported EPS history:** XBRL fact `us-gaap:EarningsPerShareDiluted`, three-month
  duration context (84–98 days), no dimensional segment, from the issuer's original 10-Q or
  10-K (never an amendment).
- **Event workspace:** the issuer's company-intelligence event workspace (SEC Exhibit 99.1,
  refreshed every three hours by `.github/workflows/company-intelligence.yml` through
  `scripts/refresh_event_workspaces.py`; read via `read_current_event_workspace`).
- **Descendants:** the composer's `financial_facts` and `publication_seam` legs are SEC
  descendants. Neither is a feature here (`financial_facts` covers AAPL only — not common
  support), but both are removed with family `S` in every ablation.

### §3.3 Label

`Y(e) = sign(EPS_dil(q) − EPS_dil(q−4))`, both values taken from the **same** original
filing for `q` (its current and comparative three-month contexts).

- Read at the first evaluator run after that filing is accepted. If no such filing with
  both contexts exists 120 days after `q`'s period end, `NOT_EVALUABLE(label_unavailable)`.
  Fiscal-Q4 10-Ks frequently tag only annual durations; those episodes land here and are
  counted.
- `EPS_dil(q) = EPS_dil(q−4)` exactly → `NOT_EVALUABLE(label_tie)`, counted.
- **Known basis mismatch (limit):** the label is GAAP diluted EPS; the expectation values
  are on the provider's basis (often adjusted). This is reported, not corrected.

## §4 Arms, baseline, common support, ablations

Each arm emits `+1`, `−1`, or `ABSTAIN(reason)`.

| Arm | Definition | Families read |
|---|---|---|
| **A0** persistence | `sign(EPS_dil(p) − EPS_dil(p−4))` for the most recent `p ∈ {q−1, q−2}` whose original filing (both contexts) was accepted `<= C(e)`; else `ABSTAIN` | S |
| **A1** expectation | `sign(average − year_ago)` from the §3.1 group; equal values or a missing value → `ABSTAIN` | K |
| **A2** composed answer | `A1` if **K-backed**; else `A0` if **S-backed**; else `ABSTAIN` | K, S |
| **A2[−K]** | `A0` if S-backed; else `ABSTAIN` | S |
| **A2[−S]** | `A1` if K-backed; else `ABSTAIN` | K |

- **K-backed(e):** A1 emits, the group's `system_observed_at >= C(e) − 4 days` (the
  composer's `STALE_DAYS`), `expectation_state = CURRENT`, identity gate `CHECKED`,
  `rights_class` not blocked, and the attempt `status = success`.
- **S-backed(e):** A0 emits, and the event workspace as of `C(e)` resolves to the issuer's
  `q−1` release with a non-empty source sha256.

**Descendant-aware ablation rule.** Removing a family removes every leg, feature and gate
computed from it, including derived workspaces. The label is never ablated. An ablation
that leaves any descendant input in place is invalid and is not reported as an ablation.
The evaluator must emit, per arm, the manifest of inputs it read, and must assert that an
ablated arm's manifest contains no record of the removed family.

**Common support (primary).** Episodes where A2[−K] emits (S-backed) and the label is
`±1`. Theme legs (`theme_tape`, `company_theme_exposure`) are not features: they are
GLOBAL or UNKNOWN for four of the five issuers and do not discriminate. `capital_structure`
is held and is not read.

## §5 Useful effect, uncertainty, costs

**Primary statistic.** `Δ = HR(A2) − HR(A2[−K])` on common support, where `HR` is the
fraction of episodes whose forecast equals `Y(e)`. Because A2 equals A2[−K] whenever
K-backing fails, `Δ` is exactly the expectation family's contribution inside the composed
answer.

**Uncertainty.** Cluster bootstrap over clusters (§6), `B = 2000`, seed `31`, percentile
interval on `Δ`. Discordant-pair counts (A2 right / A2[−K] wrong, and the reverse) and
their exact two-sided sign-test p-value are printed alongside, as descriptive.

**Minimum to adjudicate.** At least 40 common-support episodes **and** at least 12
clusters. Below that every read is `INCONCLUSIVE(minimum_not_met)` with counts.

**Looks.** At most two adjudicating looks: look 1 is the first read at which the minimum
is met; look 2 is the first read at which common-support episodes reach 80. The
family-wise one-sided error for each direction is 5%, split equally across the two looks
(Bonferroni), so each look's decision interval is the 2.5th–97.5th bootstrap percentile.
Look 1 stops the study only on `PASS_FOR_REVIEW` or `ADVERSE`; otherwise the study
continues to look 2, whose verdict is terminal. If one read first meets both thresholds,
it is look 2 and there is no separate look 1. Every other read is descriptive monitoring
and cannot stop the study.

**Verdicts (per look; the rows partition every outcome).**

| Verdict | Condition |
|---|---|
| `INCONCLUSIVE` | minimum not met |
| `PASS_FOR_REVIEW` | minimum met, `Δ >= +0.10`, and 2.5th percentile `> 0` |
| `ADVERSE` | minimum met and 97.5th percentile `< 0` |
| `NULL` | minimum met, not `ADVERSE`, and `Δ < +0.10` (including an interval above 0) |
| `INCONCLUSIVE` | minimum met, `Δ >= +0.10`, and 2.5th percentile `<= 0` |

**Useful effect.** `+0.10` hit rate (ten percentage points) over A2[−K]. A smaller
positive point estimate is reported as `NULL` even when its interval excludes zero — never
as a weak pass.

**Costs (secondary, descriptive only).** An economic translation of A2: long the issuer
when A2 = `+1`, short when `−1`, against its benchmark (`XLK` for AAPL, `XHB` for the
homebuilders), entered at `C(e)` and exited at the close of the first full session after
`t_rel(e)`, charged 10 bps per side per leg (the repository default `cost_bps = 0` is not
used). Its deflated Sharpe (`engine/validation.py` `deflated_sharpe`, `n_trials` = the
registered budget, effective sample from `bootstrap_effective_t`) is printed with an
explicit note that at this sample size it carries no decision weight.

## §6 Sample dependence, exposure, NOT_EVALUABLE accounting

- **Independent N is episodes, never rows.** One episode contributes exactly one row to
  every statistic, whatever the number of expectation captures, workspace revisions or
  filings behind it. The evaluator asserts this uniqueness on `(issuer, q)`.
- **Clusters.** `(calendar quarter of t_rel, driver family)` — at most two clusters per
  calendar quarter. Homebuilders share one cluster because their outcomes co-move.
- **Every read prints:** eligible episodes; EXPOSED exclusions; each `NOT_EVALUABLE`
  reason with its count; each arm's emit count and `ABSTAIN` reasons; common-support N;
  cluster count; `Δ` with interval; secondary contrasts; per-family splits.
- **Secondary contrasts (descriptive, no verdict):** `HR(A1) − HR(A0)` where both emit;
  coverage and hit rate of A2[−S] versus A2[−K]; the primary contrast split by driver
  family (AAPL; HOMEBUILDERS), flagged as tiny-N.
- **Exposure ledger.** The evaluator records, per episode, the first time any label value
  was read. A label read before its episode's adjudicating look is permitted only by the
  evaluator itself; a human or agent label read outside the evaluator marks the episode
  EXPOSED.

## §7 Adversarial cases and stated limits

| WP31 adversarial case | How this design answers it | Residual limit |
|---|---|---|
| (a) Row count equals independent N | §6 one-row-per-episode assertion; cluster minimum | Repository guard counts configs (`effective_n`), not episodes; the evaluator's assertion is the only episode guard |
| (b) Trials hidden after a bad result | Budget row written before any label exists (§8); append-only, tamper-protected `data/trial_ledger.jsonl`; every arm and contrast printed on every read | Vault peeks are not wired into `effective_n` |
| (c) Descendant feature remains during source ablation | §4 family→descendant map; per-arm input manifest; ablated-manifest assertion | No repository-wide descendant-aware ablation guard exists; enforcement is evaluator-local |
| (d) Backtest alone certifies live skill | No backtest: prospective episodes only; EXPOSED history excluded; a PASS buys a review | — |
| (e) Research prompt affects the portfolio while labelled read-only | The evaluator writes only its own report; no ranker, sizer, gate or surface reads it; the composer stays disabled | A future consumer needs its own promotion review |

Further limits carried from the WP31 census (C19, base `94d5771fe4f1`): there is no shared
preregistration template (this document follows `research/PROPHET_DOORS_PREREG.md`); no
consumer audits `info_cutoff`; `engine/validation.py` has no named owner; there is no
config-file admission route; `scripts/check_trial_registration.py` scans only the
`scripts/` tree, so the evaluator must live there or register explicitly.

## §8 Admission and trial accounting

1. **PREREG_COMMIT** is the squash-merge commit of this document on `main`.
2. **PREREG_DOC_SHA256** is the sha256 of this document's frozen prefix: every byte up to
   and including the §10 amendments heading line and its newline (the same frozen-prefix
   rule as `frozen_prefix` in `engine/entry_radar/replay/gates.py`). It is recorded in the
   pull-request body and the C19 ledger, never inside this document.
3. **Family and budget.** Family `c19_wp31_incremental_information`, budget `6`, basis
   `itemized`: (1) primary `Δ`; (2) `HR(A1) − HR(A0)`; (3) A2[−S] versus A2[−K];
   (4) economic translation of A2; (5) primary split AAPL; (6) primary split HOMEBUILDERS.
   An amendment that adds a contrast logs an additional budget row; budgets only rise.
4. **Registration act.** The evaluator writes the budget row through
   `engine.trial_ledger.register_trials("c19_wp31_incremental_information", budget=6,
   reason="w5_prereg=<PREREG_COMMIT> doc_sha256=<PREREG_DOC_SHA256> ...")` before it reads
   any label, on the lane that owns trial-ledger appends — never from a sparse worktree.
5. **Evaluator refusals (mirroring G-1/G-2/G-3).** The evaluator embeds both constants and
   refuses to run unless: the frozen-prefix sha256 of this file matches; `PREREG_COMMIT` is
   40-hex and an ancestor of `HEAD` (fail-closed on probe error); and the ledger holds a
   `declared_budget` row for the family whose reason carries both values, alongside
   pre-existing families (anti-truncation). Its frozen-prefix marker constant is the §10
   heading of this document, not the entry-radar §16 marker.
6. **No evaluator ships with this document.** Building it — including choosing the SEC
   XBRL reader through the existing owner — is the next WP31 action, with its own census.

## §9 Owners, natural clock, what this is not

- **Producers (existing, unchanged):** the nightly k3e capture; the three-hourly
  company-intelligence workflow; the issuers' own SEC filings. No new capture harness and
  no invented schedule.
- **Clock:** the first eligible episodes are the five issuers' next scheduled quarterly
  releases after merge. Labels mature with the issuers' 10-Q/10-K filings.
- **Not:** a trading signal, a ranker input, a forecast product, a validation of the
  composer, or a claim about any issuer. A terminal verdict is a statement about these
  arms on these episodes inside these windows, nothing wider.

## §10 Amendments (append-only, prospective only)

*None.* Each amendment is dated, states its reason, applies only to episodes whose release
time follows the amendment's merge, and never edits text above this heading.

*(The line above records the state at registration. Amendments A1–A4 below were adopted
together on 2026-10-18, before any eligible release, and without reading any label `Y(e)`,
any arm output, or any post-registration release of a universe issuer.)*

### A1 (2026-10-18) — K rights: an allow-list over both consumed rows

*Operationalizes §4 K-backed: "`rights_class` not blocked".*

**Reason.** §4 does not name the vocabulary. The K producer writes no license label today
(`collectors/equity_revisions.py` writes `UNKNOWN`), and the engine reads a missing label
as `UNKNOWN` (`SOURCE_USE_RIGHTS_UNKNOWN`): a labelled absence, not a block. A deny-list
built from the K surface's blocked vocabulary fails open on a label nobody anticipated.

**Rule.** The A1 group consumes two rows: the `average` row and the `year_ago` row. Each
row's label is read with a missing or empty value as `UNKNOWN`, stripped and upper-cased.
If the two labels agree, that label is the group's `rights_class`. If they disagree, the
group's `rights_class` is `MIXED:<a>,<b>` (sorted). The group is not blocked only when
its `rights_class` is in the allow-list `{UNKNOWN}`. Every other value is blocked, and
the episode is not K-backed. That covers the K surface's blocked and display-only
vocabulary, any unrecognized label, and every `MIXED:` value.

**Scope.** `DEC:ITP-R1-COMPLETE-DEGRADED-2026-10-07` is scoped to the R1 study and does
not bind this rule. Admitting a new label to the allow-list is a further amendment.

### A2 (2026-10-18) — `t_rel` from the EDGAR submissions clock

*Operationalizes §1 "EDGAR acceptance timestamp (converted to UTC)" and §2 rule 1.*

**Reason.** The episode source carries the EDGAR submissions-JSON `acceptanceDateTime`.
On non-universe filers, it was compared with each filing's SGML header
`<ACCEPTANCE-DATETIME>`, which is America/New_York local time. The JSON value reads
later than true UTC by the New York offset: 4 hours under EDT, 5 under EST. The checked
filings were MSFT `0001193125-26-323632` and `0001193125-26-191457`, and JPM
`0001628280-26-065582` and `0001628280-26-048078`. For example, MSFT's header reads
`20260729160453` (16:04:53 EDT, which is 20:04:53Z), while its JSON reads
`2026-07-30T00:04:53Z`.

Read literally, the JSON value moves `t_rel` later. A release filed during the regular
session would then sit after that session's close, and that close would become `C(e)`.
The release would leak into its own cutoff.

**Rule.** Let `J` be the stored value, parsed as UTC. Let `o = −utcoffset_ET(J)` and
`U = J − o`. `U` is `t_rel` only when `−utcoffset_ET(U) = o`. Otherwise the clock is
unresolvable: this happens in the hour around a daylight-saving change. A missing or
unparseable value is also unresolvable. A filing with an unresolvable clock mints no
episode, and it is handled as a dropped filing under A3.

Pins:

| `J` | Result |
|---|---|
| `2026-07-30T00:04:53Z` | `2026-07-29T20:04:53Z` (EDT) |
| `2026-01-29T02:04:38Z` | `2026-01-28T21:04:38Z` (EST) |
| `2026-03-08T09:00:00Z` | unresolvable |
| `2026-11-01T08:00:00Z` | unresolvable |

**A0 history.** Arm A0's prior-filing acceptance times are read uncorrected. Uncorrected,
they read 4–5 hours later than true UTC. The `<= C(e)` test can therefore only exclude a
filing that was in fact available, never admit one that was not. The error is conservative.

**Upstream.** `collectors/edgar_earnings_8k.py` labels the submissions value "UTC" and
stores it unconverted. That is recorded as an open gap. This amendment corrects the clock
in the evaluator and does not depend on the collector. A change that makes the collector
store true UTC must remove this correction in the same change. Applied twice, the
correction would move `t_rel` 4–5 hours early.

### A3 (2026-10-18) — the episode is defined by the first release filing, or not at all

*Operationalizes §1 "defined by the first SEC filing".*

**Reason.** The episode source drops some Item 2.02 8-K rows for `(issuer, q)` before an
episode is minted: a row without an Exhibit 99.1 attachment, or a row whose clock A2
cannot resolve. If such a row was the first filing, the kept filing is a later one.
Using the kept filing would shift `t_rel` and `C(e)` past the actual first release.

**Rule.** Take every dropped Item 2.02 8-K row with the same `(issuer, q)` as an
episode's kept filing. Skip a row with the same accession as the kept filing. If any
remaining row was accepted at or before the kept filing, or has no resolvable clock,
then the episode is `NOT_EVALUABLE(earlier_release_filing_dropped)`. Its `t_rel` is never
shifted to the dropped row. An episode already `EXPOSED`, or already `NOT_EVALUABLE` for
another reason, keeps that status. A later dropped row changes nothing.

**Limits.** A quarter whose only rows are dropped mints no episode, so it appears in no
count. A row the source cannot attribute to a fiscal quarter (no `report_date`) cannot be
matched to an episode.

### A4 (2026-10-18) — the `+0.10` comparison is exact

*Operationalizes §5 "Useful effect" and the verdict table.*

**Reason.** Hit counts are integers, so `Δ = d / n` exactly. A floating-point subtraction
can land just below a boundary the hit counts reach exactly. For example, 24/40 against
20/40 gives `Δ = 4/40 = +0.10`, but `0.6 − 0.5` evaluates to `0.0999…`. That would report
`NULL` where the table says `PASS_FOR_REVIEW` candidate.

**Rule.** The verdict compares the exact rational `(hits(A2) − hits(A2[−K])) / n` with
`1/10`. The floating-point `Δ` is printed for display. The bootstrap interval is compared
with 0 only, as before. Every read prints the exact `Δ` as `d/n` beside the float.
