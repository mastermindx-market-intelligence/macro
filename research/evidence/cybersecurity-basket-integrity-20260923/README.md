# Cybersecurity basket integrity — 2026-09-23

## Decision

Expand the canonical US cybersecurity **monitoring/breadth basket** from 10 to 14 active names:

- retained: `CRWD PANW FTNT OKTA QLYS ZS S NET RBRK TENB`
- added: `CHKP SAIL VRNS NTSK`
- reviewed but not admitted to the core: `RPD`

The basket remains **equal-weight by design** because its job is to measure participation and rotation, not to prescribe portfolio weights. A separately validated investable weighting policy can consume this universe later; this change does not create one implicitly.

Diversified platform companies such as `MSFT`, `CSCO`, `IBM`, `GOOGL`, `AMZN`, and `AVGO` remain valid product-exposure names in cybersecurity subtheme heatmaps, but they are not members of the cybersecurity-focused core basket.

## Why the old 10-name basket was incomplete

The old set represented endpoint/XDR, network firewalls, IAM, vulnerability management, zero trust, edge security, and cyber-resilience. It underrepresented four important public-market sleeves:

| Gap | Added name | Role |
|---|---|---|
| Mature network security | `CHKP` | established firewall/network-security pure play |
| Identity governance | `SAIL` | entitlement, identity lifecycle, and governance controls |
| Data security | `VRNS` | DSPM and data-access intelligence |
| SSE/SASE | `NTSK` | cloud-native security service edge and SASE |

The current holdings of two primary cybersecurity ETFs independently place `NTSK`, `SAIL`, and/or `VRNS` among meaningful positions:

- Global X BUG holdings, 2026-09-18: https://www.globalxetfs.com/funds/bug
- WisdomTree WCBR holdings, 2026-09-17: https://www.wisdomtree.com/investments/etfs/megatrends/wcbr

These ETF holdings are corroboration, not the admission rule. Admission also required local price coverage, coherent downside co-movement, thesis fit, and point-in-time membership stamps.

## Quantitative evidence

`verify.py` cuts all price series at 2026-09-23 and compares the old 10, the selected 14, and a 15-name variant containing `RPD`. The committed `results.json` is the exact output.

### Breadth on the questioned session

| Set | Equal-weight return | Advance / decline / flat | Top-three absolute contribution share |
|---|---:|---:|---:|
| old 10 | +3.85% | 10 / 0 / 0 | 53.8% |
| selected 14 | +3.44% | 14 / 0 / 0 | 43.0% |
| selected 14 + RPD | +3.62% | 15 / 0 / 0 | 39.2% |

The expanded set confirms the move was broad rather than a narrow artifact of the old constituents. The preferred deep OHLCV store shows every selected member advancing on the questioned session; no negative member was hidden or imputed.

### Proxy fit

Annualized tracking error fell when the four missing sleeves were added:

| Proxy / window | old 10 | selected 14 | 14 + RPD |
|---|---:|---:|---:|
| CIBR, 1y | 21.2% | 20.7% | 21.7% |
| BUG, 1y | 13.4% | 12.0% | 12.7% |
| WCBR, 1y | 12.6% | 12.0% | 12.5% |
| CIBR, full | 19.5% | 16.1% | 16.4% |
| BUG, full | 16.5% | 13.4% | 13.1% |
| WCBR, full | 13.0% | 11.2% | 10.9% |

The four-name expansion improves near-term tracking error against all three references and improves full-history correlation/tracking error. Adding `RPD` worsens every one-year tracking-error comparison versus the selected 14. Because an equal-weight monitor would give the smaller, lower-liquidity name the same weight as the platform leaders, `RPD` remains a coherent watch candidate rather than a core constituent.

## Candidate admission receipt

`candidate_verification.json` freezes the pre-admission run of the repository's existing `scripts.verify_basket_additions` cohort bar. All five reviewed names passed its coverage/co-movement floor. Passing that bar was necessary, not sufficient: product-role coverage and incremental proxy fit selected four names and left `RPD` outside the core.

All accepted names have a current local price store through 2026-09-23. `SAIL` and `NTSK` retain honest post-IPO `added` masks; `curated_added` records the 2026-09-23 decision separately. `CHKP` and `VRNS` use the established back-projected index convention while preserving the same honest curation date.

## Canonical projection and browser proof

The full canonical basket build was run after the membership and price-store changes. The generated `site/basket/cybersecurity.html` now carries:

- 14 configured, in-panel, and observed members; coverage `1.0`, status `complete`;
- all four additions in the holdings table and no diversified adjacent-platform leakage;
- CIBR reference correlation `0.92` and relative correlation `0.89` over 774 observations;
- the questioned session as broad participation rather than a narrow leader artifact;
- the existing theme-level read (`DOMINANT`, high breadth, low rollover risk) without pretending that this membership lane changes the separate entry/action policy.

The isolated worktree does not carry the generated per-stock library. To preserve the existing holdings experience, the final page was rebuilt against the production R2 `stockdata` records for the 12 names currently covered there. `SAIL` and `NTSK` remain explicitly `not covered yet`; that is a disclosed per-stock-library gap, not a bearish verdict. The committed regression requires exactly those two — and no established member — to be uncovered.

`browser_verify.py` exercised the real generated page in eight combinations: desktop/mobile × dark/light × English/Chinese. Every case returned HTTP 200, rendered all 14 members, excluded the six adjacent diversified platforms, had no horizontal overflow, no console errors, and no failed requests. Full-page and holdings-only screenshots plus `browser_receipt.json` are committed beside this report.

**Projection ruling:** the PR keeps the source-of-truth membership, required price stores, and the directly visible cybersecurity detail page. It does not freeze the rebuild-wide market corpus (`baskets.json`, allocation/radar feeds, and 44 unrelated theme pages), because those files advanced unrelated live market state during the same full build. The ordinary publish pipeline will regenerate those aggregate projections from the new canonical membership. Cost if wrong: a shared list surface can remain on the prior member count until that normal publish runs; the direct detail path and canonical source are already coherent.

## Scope boundary

This lane changes canonical membership, point-in-time provenance, generated basket projections, and regression coverage. It does **not** duplicate the action-semantics work already owned by:

- PR #7669 — recommendation versus stock-entry constraints;
- PR #7798 — hottest-desk leadership versus entry rating.

The desired combined user read remains: **leading and broadly confirmed; hold existing exposure; do not chase a vertical entry; low rollover risk**. Membership integrity and recommendation semantics stay separate systems with explicit owners.

## Reproduce

```bash
python research/evidence/cybersecurity-basket-integrity-20260923/verify.py
python -m pytest -q \
  tests/test_cybersecurity_basket_integrity.py \
  tests/test_basket_membership_stamps.py \
  tests/test_baskets.py \
  tests/test_basket_membership_pit.py \
  tests/test_us_basket_membership_pit.py

# In another shell: python -m http.server 18873 --directory site
MMX_BROWSER_BASE=http://127.0.0.1:18873 \
  python research/evidence/cybersecurity-basket-integrity-20260923/browser_verify.py
```

Original build Skillpack pin: `mastermindx-market-intelligence/Mastermind@a7d2b3049e5cdc523e91e61a6e9d70a1cb911157`.

## Sol continuation — 2026-09-24

The current-base integration and CI-contract repair were performed under the freshly pinned protected Skillpack
`mastermindx-market-intelligence/Mastermind@819abc8c23609cdded2b33f6e1bfc7854bd5c847`
(Skillpack 1.0.1, bootstrap major 1). Required procedures were loaded from that same immutable pin.

The branch was merged normally with protected Macro main `13c8ad3ca12b685bc639ddcb339efa8763eab42c`.
The sole content conflict was `site/basket/cybersecurity.html`: main's later nightly projection still carried the
incomplete 10-configured / 8-observed panel for the same 2026-09-23 session, while this carrier repairs the
underlying canonical membership and close coverage and projects 14 configured / 14 observed names. The
14-name feature projection was therefore retained; no recommendation, scoring, entry, or sizing source was
changed. The new regression suite was also wired into the incumbent `engine-render-guards` data/render lane,
closing the exact `contract-delta` failure without creating another CI job or waiver.
