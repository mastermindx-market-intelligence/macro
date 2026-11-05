# FIF C2 coverage freeze — 250 deep / 1,000 core (2026-10-18)

Status: **prep-only until A1.** This freezes the measured C2 census against the
masterplan §8 targets. The targets are not editable here: **250 deep and 1,000
core stay the target.** Where the measurement falls short, a measured tier
proposal is recorded and the target is preserved.

## Census identity

| field | value |
|---|---|
| cutoff | 2026-10-18T00:00:00Z |
| source generation | census-20261018-2026-10-18T20:47:45Z |
| run | census r3d (public SEC EDGAR only, ≤2 req/s, cache-backed replay; 0 network GETs in r3d) |
| outputs (sha256 prefix) | tiers.json `b2893cbac7c7f895cece` · universe.csv `97812b8837c39e062b7f` · slots.csv `cee16f447bef899165cd` · economics.json `a57d50071c407a3ed2c1` · print `f1b0eb850f757c230ffe` |

No filing bytes or non-AAPL values are in git. Only the counts, rates and
hashes above are recorded here.

## Tier membership (R3 ruling)

- **Core rule:** the 15 mandatory issuers first, then sp500 → sp400 → sp600,
  ordered by (cik_int, ticker), up to 1,000.
- **Deep rule:** mandatory issuers first, then sp500 ∩ core, up to 250. Deep is
  always a subset of core.

| tier | measured | target |
|---|---|---|
| universe candidate rows | 1,505 | — |
| core | **1,000** | 1,000 |
| deep R1 | **250** | 250 |
| deep R2 | **250** (15 mandatory CIKs) | 250 |
| exclusions | cik_disagreement 6 · ticker_unresolved_sec 5 · not_in_edgar_fundamentals 4 | — |

**Known gap:** SNOW is mandatory but sits outside the index universe. It is
flagged `mandatory_outside_universe` and is a D0 universe gap.

## Windows and metrics

- **Deep window:** N=2 annual + M=2 interim slots (A1, A2, I1, I2).
- **Core window:** N=1 + M=1 (A1, I1).
- **Metrics:** 50 in total, 40 direct and 10 formula.
- **Specialist N/A:** applicability is a predicate, not a missing cell.
  - PK11 applies to financials.
  - PK12 applies to biotech.
  - PK10 applies to proxy filings.
  - N/A cells are excluded from the denominator. Absent cells are included.

## Field presence (the measured shortfall)

| scope | present / applicable | rate |
|---|---|---|
| deep (A1+A2+I1+I2) | 79,385 / 124,850 | 63.6% |
| core (A1+I1) | 62,928 / 99,850 | 63.0% |
| issuers with every applicable field present | 0 deep · 0 core | — |

Absent rate by class, across core A1+I1 slots:

| class | absent rate |
|---|---|
| reit | 61.0% |
| bank | 55.0% |
| insurer | 53.8% |
| other financial | 47.7% |
| general | 32.1% |
| biotech | 31.7% |

The most-absent fields are the debt family: cash_to_total_debt, net_debt,
debt_to_equity, total_debt and short_term_debt (1,628–1,997 slots each). Next
come short_term_investments, operating_expenses and R&D expense.

**Tier proposal (target preserved):**

1. Membership meets 250 / 1,000 today.
2. Field completeness does not.
3. The proposal is to ship coverage as a **measured per-issuer field-presence
   tier**, published alongside the issuer instead of being implied by tier
   membership. The rule is no fabrication: absent stays absent and N/A stays
   N/A.
4. Repair order:
   - (a) the debt-family concept mapping, which is the largest single lever;
   - (b) bank, insurer and REIT statement shapes, through specialist packs
     PK11 and PK10;
   - (c) the SNOW D0 universe gap.
5. The 250 / 1,000 complete-coverage target stays the acceptance target.

## Economics (measured vs design)

| measure | design assumption | measured |
|---|---|---|
| deep bytes / issuer | 10,833,964 | mean 79,787,886 · median 62,634,326 · p90 151,492,983 · max 375,881,775 |
| deep fleet (250 issuers) | ≈2.52 GiB | 19,946,971,530 B ≈ 18.6 GiB |
| core bytes / issuer | 5,416,982 | not separately sized in r3d |
| cold GETs, deep | 7,250 | 5 per issuer (1 submissions + 4 indices) before documents |

The measured deep package is about **7.4× the design assumption**. The capture
and storage budget must be re-sized before A1. The design number is not edited
here; this table is the evidence for that re-sizing.

## Latency targets (unchanged, unmeasured in census)

| step | target |
|---|---|
| discovery | p95 under 2 min |
| capture | under 5 min |
| statements | under 10 min |
| packet | under 15 min |
| warm read | under 2 s |
| cold read | under 5 s |

## Repair notes

- **r3b, r3c:** census lane repairs at the seat.
- **r3d:** one-line seat fix to the phase-6 slot index. The flat dict became a
  nested `defaultdict` after a `KeyError 'A1'`. No logic or threshold change.
