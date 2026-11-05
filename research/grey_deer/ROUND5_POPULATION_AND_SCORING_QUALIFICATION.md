# Prophet: population integrity and shared-downside evaluation

Date: September 11, 2026 UTC. Sol research continuation, parent operation
`prophet-absolute-downside-research-20260910-sol-001`, existing Macro PR #7043.

**Disposition:** partial metadata qualification and a synthetic scoring-method
falsifier. No new empirical market experiment, live-source repair, new canonical
reader/grader, model promotion, trading authority or production acceptance.
The archive pilot's NO_INCREMENTAL_SUPPORT result remains unchanged.

## 1. The concrete measurement boundary recovered

The canonical B1 episode registry is not interchangeable with the ranked Prophet
board. Its accepted binding decision allows only a full, uncapped TURN WATCH
observation with an evaluated fired trigger and complete structural anchor to open
a natural episode. Other candidates, Doors and unanchored Radar observations may
attach to an existing episode or become suppression records. [R1]

Therefore an inner join that retains only board rows having a B1 episode can alter
the population under evaluation. This is a demonstrated contract mismatch, not a
claim that a current research job already performs that incorrect join. The exact
size or return bias of such a join has not been measured here.

The B1 acceptance probe also explicitly separates `opened_at`/`opened_session`
from `decision_at`, `tradable_at` or `decision_cut`, which its schema deliberately
does not provide. An opening event's time is not permission to assume an executable
entry at that time. [R2]

The separate W3 race retains a native (date,ticker) buy-population diagnostic at
H=10 and has its own reporting/maturity gate. That is a different measurement
object, not authority to choose a new trade horizon. W3 comparative outcomes were
not accessed in this continuation. [R3]

**Implementation recommendation for the existing research owner:** start from the
unchanged owner-defined board opportunity set; attach lawful episode relationships
without dropping unlinked or provisional rows. Retain typed absent/provisional
relations. Do not mint substitute episode IDs, merge populations or treat structural
suppression as a failed trade. Plans, board observations, expert events and B1
lifecycle episodes remain separate record kinds.

## 2. What the three published metadata objects actually establish

At Macro `4b1f8fddcc4eb6f36133fca4d42018678b74d30b`, the inspected HEAD names:

`peg:5a1d60fdd7f6d525a205560891ff68a556b9aabb81ff4e3f2cbf81929c6e1737`

| Read object | Exact Git blob | Bytes |
|---|---|---:|
| `data/us_prophet_rank/episodes/HEAD.json` | `2425f477a0a441bf05b5e663da18e0487cc8d114` | 310 |
| Named generation's `manifest.json` | `ff5bc1858133f3f8a7fd0f3c1a782ec766501d27` | 1110 |
| Named generation's `latest_receipt.json` | `2d9d09133f0c2e20635cbfab33b982739bda7226` | 2765 |

A one-shot calculation over copies of these three already-read objects passed
**25 checks**: exact copied bytes against Git blob hashes; HEAD and manifest
self-hashes; generation identity from declared file descriptors; HEAD-to-manifest
and manifest-to-receipt binding; receipt size; declared projection/upstream hash
agreement; and event/source-count arithmetic. The original 24-check pass was
extended to include the generation-address-from-file-descriptors check.

The receipt is recorded at **2026-09-06T11:16:58Z**. It reports 6,666 input
observations, 990 mapped and 5,676 suppressed; 990 appended events take the event
ledger from 1,780 to 2,770. Its source breakdown is:

| Source | Input observations | Mapped | Suppressed |
|---|---:|---:|---:|
| Candidate observations | 4440 | 588 | 3852 |
| TURN WATCH | 2221 | 400 | 1821 |
| Doors | 5 | 2 | 3 |
| Entry Radar | 0 | 0 | 0 |

These are the receipt's observation/event counts, **not unique stocks, trade
outcomes or a market-data failure percentage**. Entry Radar's source receipt
explicitly says `MISSING_SOURCE_FILE` / degraded. Candidate inputs refer to
July/August/September partitions; the TURN WATCH receipt names a September 4
snapshot. None of these dates is silently refreshed to the date of our read. [R4]

### Qualification limits

The checks establish consistency of three objects and their declared links only.
The other generation members and upstream source contents were not validated;
JSON/parquet projection parity, semantic event replay and full canonical-loader
validation have not run. The published receipt does not establish the currently
served production generation or the screenshot's decision-time input.

An attempted read-only preflight for the real B1 loader read its pinned source
and import dependency names. A subsequent compound import-time/package preflight
was safety-refused. It was not retried or subdivided; no repository modules were
imported, no generation was materialized, and the proposed full-loader execution
was stopped. The owned host session exited successfully. No other worker was touched.

The correct result is **partial metadata qualification**, not a broken-B1 verdict
and not a research-ready September 10 entry replay. Earlier B1 production acceptance
is not reopened by this limited later inspection. The exact unqualified leg remains
the complete, owner-issued opportunity-to-decision-to-execution composition.

## 3. A scoring rule that can detect the whole-board problem

Marginal per-stock probabilities do not determine joint downside. This continuation
turns the previous dependence example into an exact scoring counterexample.

Let K be the number of adverse outcomes among a fixed, declared set of N initial
opportunities, under an owner-defined loss event and horizon. A forecast supplies
the count CDF F(j)=P(K<=j). A normalized ranked probability score is:

`S(F,k) = (1/N) * sum[j=0..N-1] (F(j) - 1{k<=j})^2`.

This equals the CRPS of the losing fraction K/N. It is a familiar scoring method
applied to a decision-relevant transformation, not a new financial algorithm or
forecast engine. Proper-score research supports evaluating complementary target
features rather than expecting a single aggregate score to reveal every defect.
The cited applications are forecasting-method research, not evidence of a trading
edge for Mastermind. [S1,S2]

For true count CDF G, direct expansion gives:

`E_G S(F,K) - E_G S(G,K) = (1/N) * sum[j=0..N-1] (F(j)-G(j))^2 >= 0`.

The cross term vanishes because E_G[1{K<=j}]=G(j). Equality holds only when all
count-CDF values match; on this finite support they identify the count distribution.
This is strict propriety for that **count distribution**, not for the entire vector
of security outcomes. It is an expectation statement, not a finite-sample or
crisis-specific guarantee.

### Exact synthetic comparison

Twelve names each have a chosen marginal loss probability 1/5. World I has
independent losses; World C has perfectly shared all-or-none losses. The expected
losing fraction and the expected per-name Brier loss are identical in both worlds:
20% and 0.16 respectively. No market data was used to set those values.

| True world | Forecast count distribution | Expected normalized count score |
|---|---|---:|
| Shared loss | Shared loss | 0.1600000000 |
| Shared loss | Independence | 0.2563335249 |
| Independent loss | Independence | 0.0636664751 |
| Independent loss | Shared loss | 0.1600000000 |

Lower is better. Compare forecasts within the same true-world rows, not across
unrelated populations. The misspecified count distribution incurs excess expected
loss 0.0963335249 in either direction. Thus the proposed diagnostic distinguishes
this dependence error when the individual-probability scores cannot.

The standalone exact-arithmetic demonstration passed 12 synthetic unit tests.
A separate grid of 35 rational count distributions checked all 1,225 ordered pairs
against the identity, with zero failures. The algebra establishes the general
identity; the finite grid checks the numerical implementation only. No training,
calibration, new holdout or production source was accessed by this demonstration.
Three deliberate bad variants were rejected by assertion failures: using only the
mean, dropping fraction normalization, and treating missing outcomes as non-losses.

### What it still cannot measure

Two different sets of losing names can have the same loss-count distribution. The
count score does not identify which stocks fail, return severity, first-passage
ordering, executable fills, transaction costs, or portfolio utility. It therefore
supplements, not replaces, marginal stock/path and decision-policy evaluation.
A variogram or energy score is not a magic alternative: established research also
finds differing sensitivity and blind spots across multivariate scores. [S1,S2]

N must be fixed by the original opportunity contract before the outcome. Shrinking
it to later acted-on or successfully linked names changes the question and can hide
failure. Compare prospective policies on the same initial cohort; do not fill gaps
with synthetic board members. Repeated stock rows or overlapping date windows do
not become independent market episodes simply because the score is mathematically
proper. Empirical uncertainty needs the existing time/episode-aware evaluation.

### Missing outcomes remain unknown

For N=12 with 3 observed outcomes and 1 observed loss, the final total is only known
to lie from 1 through 10. Under the example independent forecast, the exact feasible
score range is about **[0.0269331, 0.5696669]**. These are identification bounds over
possible missing outcomes, not a confidence interval or a scored performance result.
Never assign missing outcomes zero loss or renormalize the denominator to 3.

## 4. A preventable operational research deadlock was identified

New Cockpit comment5629639705 classified several text matches as conflicting
accepted horizons. Its own excerpts include `Step 10D` (a campaign step), 30/90-day
biocatalyst display presets, and `resolved outcome` (a schema description).
Those are not alternative Prophet prediction horizons. A stock_desk 20-session
clock or a separate financial-intelligence reaction example also needs an actual
owner/target binding before it can govern P0C.

I posted the exact evidence correction as comment **5629917898** on the same issue.
It does not select an arbitrary horizon or take the P0C owner's authority. The
recommended classification is an unresolved target/owner binding, not a vote among
wrong-kind matches. This is an advisory correction delivered, not a consumed owner
ruling or proof that a genuine P0C dependency has closed.

The observational closed-read maintenance request does not require a new forecasting
horizon. It remains separately subject to its actual source, permission, consumer,
review and browser-proof gates. Do not convert P0C's real uncertainty into a blanket
stop on disjoint truthfulness maintenance, or use this distinction to bypass B4.

## 5. Independent review: a more precise access question

The existing non-author method-review placement returned BLOCKED_SOURCE_ACCESS on
its exact root, with no receiver/delivery/ACK/START. The inspected candidate had
capacity but its GitHub integration was not connected; the Integrator had no other
verified eligible route. This is not a completed review or compute-exhaustion proof.

Fresh repository metadata confirmed that both Mastermind and Macro are public.
GitHub's official contents contract permits unauthenticated public-resource reads.
A disconnected GitHub integration therefore does not by itself prove that an
already-authorized native Web/public-read tool is unavailable. It also does not prove
that the inspected candidate has such a tool. [S3]

Sol's same-root continuation **1789104117.935769** requests one finite check of that
specific distinction, without connecting an account, creating a downloader/bridge,
sending into an unrelated conversation, or evading a refusal. If no existing permitted
public reader can bind current procedure and the six fixed files, the correct return
is BLOCKED_PUBLIC_READ_CAPABILITY and the same placement parks. No new reviewer is
claimed, and both refused diagnostic scopes remain excluded.

## 6. Next executable boundaries

**Product:** existing Cockpit/Entry Truth owner consumes the closed-read adoption
request and the wrong-kind horizon evidence. Source adoption and real consumer/
browser proof remain owed. No new implementation writer is created here.

**Research:** preserve the full owner-native board opportunity denominator, with
B1 relationships as relationships, and qualify actual decision/fill clocks through
the existing owner. A three-object hash match is not the required complete packet.
Only then register the specific shared-downside/entry-path challenger and its
loss/horizon/utility comparison. Keep failed and withheld opportunities observable.

**Review:** consume the next material return on the same frozen-subject review root.
No result from the held W3 race, no repeat tuned variant of the consumed archive
pilot, and no newly invented source of trading authority is licensed by this report.

## Evidence sources

All R1-R4 reads use Macro `4b1f8fddcc4eb6f36133fca4d42018678b74d30b`:

- R1: `agentos/decisions/DEC-PROPHET-B1-CANONICAL-EPISODE-BINDINGS.md`, blob
  `d910d382afcdf76c8c0fb9166f1f921be5dac3d1`.
- R2: `research/prophet_v4/B1_NATURAL_ACCEPTANCE_PROBE.md`, blob
  `15f957ebb443e43f7c155602a95582068bd20de4`.
- R3: `research/prophet_fusion/W3_RACE_PREREG.md`, blob
  `dfc07bb5d1fc04bc59b46f7a8f6e43556efe7e85`.
- R4: HEAD and its named generation manifest/receipt, exact blobs in section2.
- Canonical loader source read, not executed: `engine/us_candidate_episode.py`,
  blob `fde1467add8b2e06977279e22b3745f3c3714894`, SHA256
  `f4ec4e85c24cb4d4c824833f24fbfb624a62c2f01614bcf50da2cf644fcc792b`.
- Owner evidence: issue6817/comment5629639705; correction5629917898;
  existing adoption request5628945643.

Primary methodological sources, accessed September11UTC:

- S1: Pic, Dombry, Naveau and Taillardat (2025), sections1–2 and the transformation
  framework, https://ascmo.copernicus.org/articles/11/23/2025/index.html .
- S2: Scheuerer and Hamill (2015), publisher abstract in NOAA's repository,
  https://repository.library.noaa.gov/view/noaa/22327 .
- S3: GitHub repository-contents documentation,
  https://docs.github.com/en/rest/repos/contents#get-repository-content .

Protected procedure for this continuation:
`Mastermind@068dcc1533776672844b36ffcde30fad68a4317f`, compatible Skillpack1.0.1/bootstrap1.
The exact research outcome remains subordinate to real source and production proof.
