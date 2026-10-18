# Independent WP02 source-diagnostic policy review

## Verdict

**REQUEST_CHANGES for two bounded P2 input-contract gaps before adoption/selector execution. No P1 mathematical defect found.** The principal accepted R1 and R2 for correction during this review. Corrected policy artifacts have not yet been reviewed; this is not a corrective PASS or permission to select issuers.

The recommendation is scientifically defensible as a deliberately constrained source diagnostic if its relative-size meaning is explicitly adopted and its full historical frame is actually supported. The count-band formula, higher-boundary tie rule and country/activity/size flow structure preserve the specified quotas. They do not establish that a complete lawful frame exists or that the 120-issuer design is feasible on real inputs.

The reviewer did not author the policy. Scope was scratch-only method/source review, public primary methodological reads and small synthetic arithmetic controls. There was no application/native/Git action, stock or issuer census, market-cap dataset acquisition, selector execution or vendor-output consumption. The author continues to own its frozen artifacts; no policy file was edited.

## Exact reviewed source

The first three files were copied as an immutable draft snapshot before full review; their hashes subsequently matched the author's final freeze exactly. The validation and manifest were then read and independently hashed. They do not constitute independent scientific validation merely because their structural checks passed.

| File in `lanes/source_diagnostic_policy_v1/` | Bytes | SHA-256 |
|---|---:|---|
| `RECOMMENDED_SELECTION_POLICY.json` | 31,323 | `03881ee568f6f08f06ef88a2fad0e33ff2fe14b3ab1db526c35221d642cfe9fd` |
| `SELECTION_POLICY_ADJUDICATION_MEMO.md` | 38,864 | `763f8724b1ec9e88a60b94dd65b3d61befe6af79ff28f64f472f0a87ecf9a582` |
| `PRIMARY_SOURCE_REGISTER.json` | 15,881 | `cf2521ad18316785ecd48c34cbdd132ab4606214041132548b0ff4898cfa2b43` |
| `ARTIFACT_VALIDATION.json` | 2,102 | `8042fa90e6cd48d80abdcd9a171dcc462914ed2313b1e8dc2c2d0313fbe480c3` |
| `PACKAGE_MANIFEST.json` | 1,219 | `eee4790063d4ae92d3b1b97cd3730daa4f87f0a47ad906bf1b478d8dde20951d` |

## R1 — historical roster completeness needs an operative receipt

**Severity: P2.** Locations: `relative_size.completeness`, `relative_size.denominator`, `instrument_and_venue.venue_register_requirement`, and memo §§3, 5, 7.

The text correctly requires a complete eligible denominator, excludes current-only status as automatic historical proof, and holds unresolved supplied rows. What it does not yet prescribe is an input certificate establishing that the historical issuer roster itself is complete. Checking every row in a later directory cannot detect an eligible issuer that disappeared from that directory between D and the source observation. Validity evidence for supplied rows proves row eligibility; it does not prove absence of omitted rows.

**Smallest counterexample:** a synthetic eligible D pool has values 500, 400, 300, 200 and 100. The issuer valued at 100 delists after D, so a later directory contains only the other four. Every surviving row can have correct D listing evidence and complete cap data. Yet the incomplete directory changes the 300 issuer from relative L to M and the 200 issuer from relative M to S. The arithmetic was independently executed and retained in `METHOD_CHECKS.json`; these are artificial values, not observed issuers.

**Minimal correction:** make a per-venue/per-instrument historical frame receipt required before any quantiles. It must bind either an adequately complete dated roster at D or an anchored roster plus a complete admission/removal/conversion reconstruction covering the interval to D. Required fields should identify the venue/segment perimeter, roster-as-of date, anchor source and digest/length, actual acquisition/publication clocks, event-chain bounds, reconciliation totals, known omissions and unresolved rows, source entitlement, and the accountable completeness assertion. Later current-only directories without that reconstruction return `FRAME_HISTORY_UNPROVEN` (or an equally explicit adopted code). They must not produce a complete-rank denominator.

Reconcile additions, removals, transfers and instrument/primary-status changes, rather than merely retaining an `effective_from` on surviving securities. Keep legitimate post-D delistings in the D frame, exclude post-D first admissions, and apply K to assertions/revisions. This is an operational form of the existing completeness principle, not a proposal to expand quotas or select an available subset.

## R2 — independent capitalization conflicts cannot become implicit revisions

**Severity: P2.** Locations: `capitalization.share_count.source`, `capitalization.prices`, `capitalization.share_class_and_ADR`, `cutoff_policy.revisions`, and memo §§5–6.

The policy correctly separates measurement, public availability and observation and chooses the latest eligible revision. It does not explicitly distinguish an evidenced revision chain from conflicting independent assertions by an issuer, regulator or exchange about the same component. A later publication is not by itself proof that the earlier assertion was superseded. Different implementations could choose different lawful inputs while both claiming to follow “latest.”

**Smallest counterexample:** two source assertions claim 190 million and 210 million outstanding shares of the same class, on the same measurement date and basis, both available by K, without a proved correction relation. At the same price of 10, the possible reference values are USD1.9 billion and USD2.1 billion. The absolute tag changes from S to M. With fixed synthetic companion values of 10, 3, 2 and 1 billion, the candidate also changes from relative M to L. Source freshness alone does not settle the contradiction.

**Minimal correction:** define ordering by applicable measurement date first; within that fact/date/class/basis, use a source-bound revision only where supersession is established. Retain source/assertion identities, units, class basis, actual versus estimated status, valid/public/observed clocks and explicit revision links. Unreconciled competing exact values return `CAP_COMPONENT_CONFLICT`, preserve both assertions and hold the issuer/pool. Apply the same principle to reference closes, ADR ratios, class counts, corporate-action bridges and FX revisions. Never use market-cap magnitude, quota fit or hash priority to choose a factual winner.

This does not prohibit a newer measurement from replacing an older measurement as the reference observation. The conflict key is the same economic fact/date/basis; measurements of genuinely different dates remain distinct. The policy's existing same-basis rule must also be realized as explicit component bindings when a stale pre-action close is combined with shares bridged to D. Missing action quantities or unresolved price/share basis cannot be repaired by an undocumented adjustment.

## What is mathematically sound

For descending complete-pool values, `k1=ceil(N/2)` and `k2=ceil(3N/4)` satisfy `1 <= k1 <= k2 <= N` when N is positive. Consequently `t1 >= t2`, and the three stated intervals partition positive values. Equal values at either boundary remain together in the higher applicable band. The algorithm may legitimately produce an empty M or S band; quota infeasibility is then a result, not a reason to split ties. The small-N and tied-value arithmetic was independently checked on synthetic inputs.

The 42 pools are the seven **assigned primary-jurisdiction groups** times six activities. Because multi-primary issuers are assigned before ranking, these are ranks of the administratively assigned, deduplicated frame. They must not be presented as ranks among every trading line or every company with any listing in a jurisdiction. Common-control listed issuers can remain distinct under the chosen issuer unit, but their observations are not thereby statistically independent.

The non-INT demand is 96 issuers. INT has three country capacities of eight and 18 activity/size sink capacities summing to 24. Integral full flow of 24 saturates every country and every activity/size quota. Aggregating by country/cell is valid only after each unique issuer has exactly one country and cell. In a synthetic failure example, UK candidates reach only one L cell with capacity two; JP and EU can each supply at most eight. Even generous individual candidate counts cannot overcome the cut bound of 18. No actual INT population or flow was measured by this review.

The greedy feasibility-preserving selection produces the first feasible priority list if its residual state is explicit. The following is a nonblocking implementation clarification and acceptance test requirement, not a third policy finding:

```text
require full_flow(all_candidates, country_quotas, cell_quotas) == 24
remaining = all candidates in fixed issuer-priority order
selected = []

for candidate in fixed priority order:
    remove candidate from remaining BEFORE testing tentative inclusion
    trial_country = country_remaining minus this candidate's country incidence
    trial_cell = cell_remaining minus this candidate's activity/size incidence
    if any trial quota is negative:
        reject candidate with residual-quota reason
    else:
        target = sum(trial_country) = sum(trial_cell)
        if full_flow(remaining, trial_country, trial_cell) == target:
            include candidate; adopt both trial quota vectors
        else:
            exclude candidate; retain residual mincut certificate
    stop when 24 have been selected

require all residual quotas zero and 24 unique selected issuer IDs
```

The tentative candidate cannot remain available to complete its own residual L demand. A residual test's target is the remaining total, not always 24. Test this against brute-force feasible subsets on small synthetic cases when the selector is implemented. Input-order permutations, tied values, duplicate identities and deficient cuts should be tested through that actual selector; this review did not implement it.

## Scientific interpretation and source checks

The 50/25/25 issuer-count bands, 183-day share-count tolerance, five-session/ten-day price tolerances, narrow activity perimeter and D/K/F choices are **chosen research policies**. They are not sourced market laws. FINRA explicitly presents variable cap conventions; its absolute examples can support a labelled companion classification but do not validate relative quartiles. MSCI's dated methodology uses full-cap ordering together with cumulative free-float coverage and global size bounds, rather than these count bands. [W1], [W2]

The proposed ADR conversion direction and refusal to double count underlying shares are consistent with the SEC's ratio-based definition. The ECB quotes currency units per EUR, supporting the specified cross-rate division; its rates are informational, not transaction-price evidence. No rate value from the live page was used for D. [W4], [W5]

GICS uses principal activity with revenue, earnings and review considerations. The policy correctly calls the strict >50% external-revenue fallback its own rule, and not GICS. A licensed classification route and a primary-evidence fallback can differ in availability and detail. Any unresolved/conflicting assignment must continue to block completeness; available classifications cannot silently define the eligible population. [W3]

The FY2023–2025 document exercise is conditioned on the issuer satisfying the chosen D frame. Even a perfectly reconstructed D roster does not represent every issuer that existed in each earlier source year. Report this as a D-conditioned source diagnostic, not historical-market coverage or historical issuer performance. Survivorship research provides a general reason to avoid the stronger inference; it does not quantify bias in this unbuilt study. [W6]

Likewise, D local closes, K public knowledge and actual later F remain distinct. K after D is deliberate retrospective reconstruction, not a tradable D-only strategy or evidence that Mastermind possessed inputs at K. Public-date uncertainty, code/classification histories, effective listing changes and later revisions remain explicit. Counts of complete/captured documents must retain the requested denominator and unavailable, refused, anonymous and unmatched outcomes; poor results never authorize replacements.

Relative L/M/S must always appear with their relative labels, exact reference values and absolute companion tags. A relative L issuer can be absolute MICRO. No selected name or measured eligible count was inferred from memory. Equal quota counts do not establish equal economic scale, uniform inclusion probability, independence, population-weighted performance, source truth or predictive precision.

## Cloud scope and the economic-network objective

A02's company-majority IaaS/PaaS rule is a deliberate primary-activity perimeter. A diversified company can have an economically important report-backed cloud segment without that segment being its primary activity. Such a company can be absent from the semiconductor/cloud pool, or assigned to another group, without its segment role being economically irrelevant. No actual company's eligibility or revenue share was estimated here.

This cohort therefore cannot establish coverage of all cloud demand drivers or segment-level supply-chain roles. Preserve **corporate primary activity** separately from **reported segment role** in the later network. A segment-focused or purposively chosen supplement needs its own declared case unit, inclusion rule, source/date bindings and denominator; it must not silently replace or fill the 120-issuer quotas. Do not invent segment revenues, economic weights or companywide cloud membership. The same limit applies to the six groups' other deliberately excluded activities.

## Operational feasibility, licensing and next action

The rank-frame sourcing scope is materially broader than 120 selected-company lookups: it requires the entire eligible historical perimeter for all 42 pools, including lawful cap-component evidence for candidates that will never be selected. Its actual cardinality is not measured here. A single unresolved potentially eligible row can block a pool; one incomplete required pool can block the full design. That is a deliberate anti-conditioning rule with a substantial cost, not a mathematical flaw.

No complete lawful historical cap frame is supplied or established by this policy package. The earlier accepted frame audit reports missing frame evidence; this reviewer did not rerun that census. There is no claim that all external providers lack such data. Kernel correctness and attractive rank counts do not establish actual frame feasibility, entitlement or Canadian healthcare capacity.

Require a source-owner receipt for the exact permitted use, historical access, retention, derived classifications/caps, review sharing and any later distribution. A public methodology page is not a bulk constituent/classification/price license. If a necessary frame source cannot be used lawfully, retain that failure; do not call the entitled subset the complete market. No blanket licensing conclusion or entitlement was inferred from these web reads.

The precise next step is to incorporate R1/R2 into the versioned policy/input contract, obtain principal adoption of the chosen A01/A02/A03 semantics, and commission the bounded selector against explicit complete/incomplete frame states. A schema-valid incomplete frame should return its typed holds and unresolved counts rather than attempt quantiles. Actual lawful frame sourcing is a separate necessary dependency. This uses existing accountable owners and does not require waiting for a historical owner name or repeating a permission loop.

## Evidence and limitations

Six primary methodological sources were independently opened. Their inspected portions and retrieval references are in `SOURCE_OBSERVATIONS.json`; all raw source-byte hashes are null. The sources were read as web-rendered HTML/PDF or a publisher abstract, not captured as exact source bytes. Only the narrow methodological claims below are independently supported; the author's complete 19-source register was read but not every source was independently re-fetched.

- **W1:** FINRA, [Market Cap Explained](https://www.finra.org/investors/insights/market-cap), dated 2022-09-30, definition/conventions section.
- **W2:** MSCI, [Global Investable Market Indexes Methodology, May 2026](https://www.msci.com/eqb/methodology/meth_docs/MSCI_GIMIMethodology_May2026.pdf), printed pp.26–27.
- **W3:** S&P DJI/MSCI, [GICS methodology](https://www.spglobal.com/spdji/en/documents/methodologies/methodology-gics.pdf), printed p.3, classification rules.
- **W4:** ECB, [Euro foreign exchange reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), publication/quotation-basis introduction; no historical rate series acquired.
- **W5:** SEC/Investor.gov, [American Depositary Receipts](https://www.investor.gov/introduction-investing/investing-basics/glossary/american-depositary-receipts-adrs), ratio definition.
- **W6:** Brown, Goetzmann, Ibbotson and Ross, [Survivorship Bias in Performance Studies](https://doi.org/10.1093/rfs/5.4.553), Review of Financial Studies 5(4), 1992, pp.553–580. Publisher abstract only; no full-paper or quantitative WP02-bias claim.

`METHOD_CHECKS.json` contains only the executed synthetic order-statistic/conflicting-cap arithmetic and an analytic cut bound. It is not an issuer dataset, a production selector, an actual INT feasibility result, or evidence of predictive accuracy. All policy files remained unchanged. Review state and findings are bound in the companion manifest.

**STOP.**
