# Source qualification and reuse: do not build another information engine

Status: bounded read-only qualification for the independent trough-gating study, 2026-11-14. No vendor contact, procurement, entitlement change, raw-data publication, source mutation or historical stock outcome test was performed.

## 1. The existing Mastermind capability is not zero

At inspected Macro source `2469f810b4867875b3be59fef89e980e3f0d3231`:

- `collectors/equity_revisions.py` owns current/prospective EPS expectation capture, consensus drift, revision counts, covering-analyst count, dispersion and append-only history. Its header explicitly distinguishes current snapshots from historical estimates. Fiscal-period anchors and correction lineage must be preserved; a rolling +1y label is not a stable fiscal-period identifier.
- `research/alpha_intelligence/expectation_market_dynamics/CURRENT_CAPABILITY_LEDGER.md` retains an October 3 evidence update: SRC-A1 prospective captured source accepted as PROVEN_LIVE within its frozen contract, while historical certification, rights, economic eligibility and downstream expectations/market/coupling acceptance are separate. This dated ledger is not a new live deployment audit.
- `INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md` already specifies information -> expectations -> market response, economic-link propagation, partially pooled driver sensitivities, same-information model comparisons and decision utility at matched acceptance. It explicitly rejects a new residual engine, generic conviction score, belief store or independent Market Preference engine.
- `COMMISSION_2_PIT_ANALYST_EXPECTATIONS_HARDENED_AUDIT_2026-10-04.md` distinguishes useful prospective collection from a mature historical institutional PIT archive. Its earlier census is evidence of the documented gap, not proof no later capability exists.

The precise present finding is **historical non-price joins were not qualified for this run**. It is NOT a claim that all Mastermind data is unavailable, all revisions are absent, or a new paid vendor is necessarily required.

Source links:
- https://github.com/mastermindx-market-intelligence/macro/blob/2469f810b4867875b3be59fef89e980e3f0d3231/collectors/equity_revisions.py
- https://github.com/mastermindx-market-intelligence/macro/blob/2469f810b4867875b3be59fef89e980e3f0d3231/research/alpha_intelligence/expectation_market_dynamics/CURRENT_CAPABILITY_LEDGER.md
- https://github.com/mastermindx-market-intelligence/macro/blob/2469f810b4867875b3be59fef89e980e3f0d3231/research/alpha_intelligence/expectation_market_dynamics/INFORMATION_TO_PRICE_PROGRAM_2026-10-03.md
- https://github.com/mastermindx-market-intelligence/macro/blob/2469f810b4867875b3be59fef89e980e3f0d3231/research/alpha_intelligence/expectation_market_dynamics/COMMISSION_2_PIT_ANALYST_EXPECTATIONS_HARDENED_AUDIT_2026-10-04.md

## 2. Public stock-characteristic archive: probed, not blindly adopted

The author site for Gu, Kelly and Xiu's empirical work links a stock-characteristics archive:
https://dachxiu.chicagobooth.edu/download/datashare.zip

A HEAD request and a single 65,536-byte HTTP Range request were made on the authorized M2 host. Observed archive size: 1,555,896,289 bytes. Server Last-Modified: 2026-02-26. The first ZIP member is `datashare.csv`, with declared uncompressed size 3,836,202,174 bytes. Only its CSV header was decompressed for inspection. No stock rows, forward returns or reserved outcomes were read. No full archive was downloaded or written.

The header includes permno, DATE, price/momentum/liquidity characteristics, accounting characteristics and sic2. It does **not** contain an explicit return target, a delisting-return field, daily OHLCV, the proprietary timer event, or an explicit analyst-forecast-revision field. That does not prove an acceptable target cannot be joined; it proves this header is not a ready-to-run trough dataset.

In particular, do not shift `mom1m` from a later row and quietly call it an executable total return. Exact feature timing, raw-versus-ranked status, missingness, terminal/delisting coverage, dividend basis and security identity must be established. A monthly terminal-return proxy cannot certify intramonth catastrophic-loss or 3-session timer labels.

The related Python construction project documents several raw/imputed/ranked outputs and `ret_t = chars_(t-1)` alignment, with WRDS CRSP/Compustat/IBES prerequisites. That documentation is useful but does not by itself certify that the linked author CSV has the same transformation, clock or target. The author site also states research-only/noncommercial-use restrictions. Nothing in this study grants product redistribution or commercial rights.

Sources:
- https://dachxiu.chicagobooth.edu/ (Empirical Data / Codes links and site-use statement)
- https://dachxiu.chicagobooth.edu/download/ML.pdf (data description and availability lags, p.2248 / PDF page26)
- https://feng-cityuhk.github.io/EquityCharacteristics/ (output schemas and prerequisites)
- https://github.com/Feng-CityUHK/EquityCharacteristics/blob/master/chars60_summary.csv (field definitions inspected)

This is a data-qualification finding, not an authentication denial, vendor outage, paid-data demand or assertion that all public stock research is impossible.

## 3. Minimum input proof before the next non-price stock experiment

Reuse existing owners and qualify one immutable development snapshot, without opening reserved outcomes:

1. Existing timer/event owner: security identity, first-known timestamp, bar anchoring/timezone, completed 3-session / 2-session / 2-week / monthly joins, version, episode ID and original labels. Preserve the exact dot and same-swing T1 definitions.
2. Market-response owner: corporate-action-consistent OHLCV/total returns, delistings/terminal events, executable entry convention and missingness. Do not reconstruct a second residual engine or replace a missing quote with zero.
3. Expectations owner: fixed issuer/metric/fiscal period, units/currency/accounting/share basis, source and capture clocks, coverage, estimate availability, fiscal rolls and corrections. Current estimates may not be backdated into 2013-19.
4. Company / Earnings owner: the first admissible guidance/actual release and known event-calendar state. Later restatements are not the original information set.
5. GMI / K3-D / F04: pre-existing disclosed economic links and valid-time memberships; market co-movement is a different edge type.
6. Risk Radar / macro owner: known-time rates, expected inflation, credit/dollar conditions and filtered state; revisions and future-smoothed labels excluded.

A metadata-only coverage matrix by year, type, group and source is the next qualification action. It should distinguish source NOT_FOUND, source UNPROBED, available-but-not-PIT-qualified, missing-at-event, and certified usable. No outcomes are required for that audit. If an authorized, already-qualified historical source exists, reuse it; no new procurement is implied.

## 4. Integration recommendation, not a production change

The new contribution is an empirical gate/label diagnostic and a proposed trough-specific evaluation join across existing capabilities. It is not a replacement for K3E EVAL-0, Evaluation OS/QLedger, Security State, Prophet's conditional-fusion owner or economic-relationship objects. No frozen protocol is amended by this research note. Any additional experiment must be registered through the existing owner and respect its reserved eras and trial accounting.

Do not duplicate the active incumbent TROUGH-GATES work or interpret this branch as permission to read its held-out stock/industry periods. This run consumed only pre-2003 public industry outcomes; it did not use private stock outcomes or 2026 anecdotes for validation.
