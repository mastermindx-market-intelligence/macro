# Earnings information time: research result versus a usable recommendation

**Outcome-free method review and B15 design amendment; NOT_REGISTERED / NOT_ACTIVATED.**

This phase examines WHEN new evidence can support a recommendation. It is not the
previously refused daily-versus-monthly market-trend experiment. No native H1,
Cycle, historical price panel, new trial, provider extraction, proprietary transcript
or financial outcome was read or recomputed. It amends the existing Earnings B15
research design, not the company evaluation registry or its protected trial history.

## 1. A useful hypothesis, not a shortcut to adoption

Christensen, Timmermann and Veliyev, *Warp Speed Price Moves: Jumps after Earnings
Announcements*, arXiv2601.08962v1, posted January13,2026 (manuscript dated
November2024), examine50liquid stocks using2008–2020 high-frequency data. Their
studied short-horizon surprise strategy loses significance after spread/latency
frictions in the2016–2020 subsample. This warns against awarding an entry the
pre-response price. It does not establish that every earnings strategy, stock or
longer holding horizon has ceased to work.
Source: https://arxiv.org/html/2601.08962v1 , introduction and section6.2.

Yu, Liu, Zhang and He, *Fast Numbers, Slow Language*, arXiv2606.29734v1,
June29,2026, proposes different horizons for numerical news and transcript tone.
Its stated limitations include perfect bar-open fills, primarily gross results,
no portfolio risk controls and limited small-cap coverage. Its main timing
comparison, useful as a hypothesis, must not be treated as our return evidence.
Source: https://arxiv.org/html/2606.29734v1 , sections4–6, limitations and appendixC.

The linked public repository was inspected through GitHub at
`piqueyd/Fast-Numbers-Slow-Language@78890e78b557708a7e38906a6e227c23d10cca76`:
the complete tree has only README.md, blob
`b371b25c1cb3b9f6a50f8a6c5fa7eb3fd14068a0`,2232bytes, saying code/data are coming.
We therefore cannot independently inspect its implementation or reproduce the
reported outcomes from that repository. Publication text is not a code receipt.
We did NOT copy its code or request private data. No repository mutation occurred.

## 2. Two exact mathematical cautions

The newer paper's written historical-percentile formula is
`w = (G/N)*2*(p-.5)` beyond its selected tails. That alone does NOT ensure its
stated dollar neutrality. For G=2,N=3 and percentiles .95,.92,.02, the formula
gives weights .60,.56,-.64: net+.52 and gross1.80. A common+1%market move produces
+.52%portfolio P&L even with no stock-specific information. This is a counterexample
to the stated formula's guarantee, not a claim about unavailable program code.

Its N also requires an explicit causal definition for asynchronous arrivals.
For the first .95-percentile observation, using eventual N=2 gives weight.90;
eventual N=10 gives.18. If N is learned only after the session, that earlier
allocation is not known at decision time. A fixed ex-ante budget or an explicit
sequential allocation is required. Do not solve this with a retrospective
rescaling that rewrites the original position.

Our original synthetic arithmetic checks are committed with exact Fraction
identities. They inspect no real asset returns. The paper's implementation could
have additional constraints; the absent implementation means that remains unknown.
A self-description of neutrality or positive IC is not a portfolio-risk proof.

## 3. Entry-time attribution

Define the economic information event, source availability, model decision,
qualified quote and actual allowed entry independently. The date in a release
header is not a fill price. The start time of a call is not the time the complete
transcript or a Q&A passage became available. An issuer release and a later
narrative source must not be assigned one convenient timestamp.

For comparable prices P0 before disclosure, Pu at first genuinely usable entry,
and PH at a fixed endpoint:

`PH/P0 = (Pu/P0) * (PH/Pu)`.

In a hypothetical100→110→112 path, the complete event window rises12%, but a
buyer at110 has only1.818%gross price appreciation to112. The first10%is not a
captured trade result. Conversely, the earlier movement does not prove that no
further opportunity remains. Costs, execution, market permission and a newly
qualified payoff case still decide whether the remaining opportunity is useful.
This is attribution arithmetic, not a price forecast or a new execution model.

## 4. Concrete B15 cohort specification

The existing source/evaluation owners must keep three event cohorts distinct:

A. **Guidance-update decisions** use the first usable issuer-update source and its
previous comparable revision. An eventual earnings actual is forbidden input.
The existing guidance_change computation already enforces that separation.

B. **Reported-number decisions** use comparable released financial observations
and expectations actually qualified before release. Operating change, analyst
surprise, seasonal relative strength and accounting-cash decomposition remain
separate features. The new cash reconciliation is not a prediction of persistence.

C. **Later-language decisions**, only after the existing rights owner admits the
specific source/model use, use the actual available text slice and its generated
feature time. Full-call inference is eligible no earlier than availability of the
full call artifact and processing completion. No unlicensed transcript capture
or general sentiment service is authorized here. Missing source rights block this
arm, not the factual issuer-release arms.

For each cohort, retain the same original eligible issuer/event population and
native economic identity. Record source-ineligible, not-yet-known, missing price,
entry refused, unfilled, delisted and corporate-action unresolved cases. Do not
collapse these into a zero return, remove them after observing performance, or
quote a hit rate only on survivors. Use original source/correction lineage and
qualified price/session basis; do not reconstruct with today's corrected statement.

The primary selection comparison is incremental expected utility AFTER the
first defensible decision and native entry, not full announcement-window return.
First isolate selection from execution: hold the accepted entry/holding/risk
policies fixed while adding one specified earnings family to the native price/
independent-sector baseline. Separately test entry-timing changes with selection
held fixed. Otherwise a faster source, different universe or different risk budget
can masquerade as an improved classifier.

## 5. Model proposal with bounded complexity

The first candidate is a parsimonious regularized model of benchmark-relative
return at the existing declared sleeve horizon, paired with an independently
qualified adverse-path model. Inputs are signed economic magnitudes, explicit
coverage and source clocks. Do not average favorable evidence labels. Start with
one lineage-aware financial-information increment; keep the unchanged native
model and a simple price/sector baseline as comparators. A profitability level
and its change are separate from valuation paid and from cash-flow reconciliation.

Only source-supported interactions are eligible for later nomination: for example,
profit margin change conditional on valuation, or earnings revision conditional on
independent group participation. The module's parameter count, feature family,
regularization grid, temporal partitions, numerical worthwhile gain and harm
margins must be frozen through existing Evaluation BEFORE native outcomes are
opened. This document is not the missing experiment registration and allocates
no new trial budget. Previous failures and model-selection attempts still count.

At deployment-like evaluation use original full population with unchanged base
behavior where an optional feature is absent. Also report the paired,
jointly-source-qualified subset to isolate information value. These are distinct
estimands: coverage benefit is not the same as predictive benefit on a curated
subset. Compare event arrivals sequentially; do not use tomorrow's peer winners,
later source completeness or eventual session event count in today's ranking.

## 6. Falsifiers and acceptance conditions

- Shifting later documents or prices must not change earlier frozen features,
  candidates, weights or recorded decisions. Same-day end-of-session ranking is
  a different action from an immediate asynchronous decision.
- The first executable quote must follow every required input's usable time and
  compute/transport delay. Quotes have side, size, spread and venue/session; a
  five-minute bar open is not automatically an achievable fill.
- Own-industry/issuer signals must be tested against the independent sector-only
  alternative. Leave the focal issuer out when calling peer evidence independent.
- If language is evaluated, test timestamp-constrained evidence extraction and
  model-knowledge contamination. Chronological stock splits alone do not prove
  that a later-trained language model has not memorized a historic outcome.
  Require prospective frozen outputs or defensible model/data time separation.
- Evaluate both missed opportunity and avoided adverse moves. Do not maximize
  annualized Sharpe from a small number of event sessions while ignoring capital
  held between events, exposure mismatch, borrow costs or unresolved positions.
- Test actual arithmetic portfolio neutrality/gross limits and the original
  allocation process. A percentile tail rule is not a net-exposure constraint.
- A source quotation error, wrong units, missing observations and expired permission
  cannot become a confident buying instruction. Retain the full research journey.

The uncertainty question is whether the incremental feature improves a declared
native decision AFTER information is usable and prices respond, not whether an
LLM can produce fluent explanations of winners. Confirm selection improvement
with the existing closed evaluation gate, then apply current source/market/entry/
portfolio restrictions to recommendations through their accepted native owners.

## 7. Product implications now and later

A factual earnings view should label what was already public, what is new, which
comparison is missing and what price assumptions remain untested. It should not
label a post-gap stock 'best time to buy' merely because the earlier result was
strong. The current source-bound dossier/brief supports these distinctions; its
ordinary UI installation and actual market/entry consumer proof are still owed.
The new cash reconciliation adds one concrete economic countercase without
claiming model promotion. The next source unit is matched-period financial input
coverage and accepted event timing; the next empirical unit is the admitted
same-population incremental comparison, not another unregistered strategy run.

No source/price collector, ranking gate, portfolio allocator, evaluator, model
registry, user notification or source-rights permission is created by this note.
The original B15/Company Intelligence/Data OS/Portfolio-Risk/Evaluation owners
remain authoritative. All code in this directory is research arithmetic only.
