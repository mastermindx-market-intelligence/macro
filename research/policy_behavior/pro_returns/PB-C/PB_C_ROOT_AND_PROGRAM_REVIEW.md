# PB-C root and program integration review

Review date: 2026-10-07. Scope: event identity and program membership before event tests. No statistics were run; neither input file was modified.

## Reviewed inputs

- /workspace/scratch/7a0bb715b184/pbc_tech/events.json — 49 rows; SHA-256 8ae222914bf79bae368f1c6795098a958e445a90ef90e28a3b5e3e96a7bf0d6a.
- /workspace/scratch/7a0bb715b184/pbc_controls/events.json — 38 rows; SHA-256 119789b3c2e26265b6b9f07f1bb239c476f2b03f20d65ed290755b7bb3be77ce.

These recommendations review the captured panels, not uncaptured event history. Program classifications use transaction identity and named source relationships, without event-return or stress-test inspection.

## 1. One confirmed cross-lane duplicate

| Canonical root recommended | Alias to merge |
|---|---|
| PBC-D-MP-20250715-APPLE-SUPPLY | PBC-TECH-AAPL-MP-20250715 |

Canonical choice uses the lexicographically first existing root ID; it has no economic significance. Retain both source manifestations, both issuers and each source's timestamp precision. Both originals describe the July 15 Apple purchase/recycling agreement at Independence and Mountain Pass. They are one agreement, not independent evidence of two announcements. [S2, S5]

No other cross-lane duplicate is established by the two captured panels. Named supplier/customer quotations in tech umbrella releases do not duplicate another issuer's unrelated earnings or capacity announcement. There is no separate Coherent August 6 announcement row to merge here.

## 2. Defensible shared-program families

The lists below use the canonical Apple–MP root above. They are memberships, not instructions to delete new milestones. The final two families are a regulatory-transaction and a fiscal-disclosure cycle; the export family is a common external policy process. Keep these kinds separate from commercial launch programs.

### APPLE-US-MANUFACTURING

**Kind:** SPECIFIC_ISSUER_SPENDING_PROGRAM.

**Exact member root IDs:**

- PBC-TECH-AAPL-US-INVESTMENT-20250224
- PBC-D-MP-20250715-APPLE-SUPPLY
- PBC-TECH-AAPL-US-EXPANSION-20250806

July agreement explicitly belongs to Apple's February spending pledge; August raises the same aggregate commitment. Preserve new agreement and increment as distinct roots. [S1, S2, S3]

### MP-US-MAGNETS-2025

**Kind:** SPECIFIC_LINKED_CAPACITY_AND_FINANCING_PROGRAM.

**Exact member root IDs:**

- PBC-D-MP-20250710-DOD-PACKAGE
- PBC-D-MP-20250715-APPLE-SUPPLY
- PBC-D-MP-20250716-COMMON-OFFERING

MP's Apple original explicitly relates the Independence expansion to the DoD partnership; the offering names the 10X facility as a proceeds use. The contracts and facilities remain distinct. [S4, S5, S6]

### SAUDI-HUMAIN-20250513

**Kind:** SPECIFIC_COMMON_SPONSOR_AND_ANNOUNCEMENT_PROGRAM.

**Exact member root IDs:**

- PBC-TECH-AMZN-HUMAIN-20250513
- PBC-TECH-NVDA-HUMAIN-20250513
- PBC-TECH-AMD-HUMAIN-20250513
- PBC-D-CSCO-20250513-HUMAIN

Four original releases name HUMAIN and the same Saudi infrastructure launch. Cisco explicitly connects its announcement to the presidential visit. Separate supplier agreements are not separate independent program origins. [S7, S8, S9, S10]

### STARGATE-US-BUILDOUT-2025

**Kind:** NAMED_INFRASTRUCTURE_PROGRAM.

**Exact member root IDs:**

- PBC-TECH-ORCL-STARGATE-20250121
- PBC-TECH-MSFT-OPENAI-20250121
- PBC-TECH-ORCL-STARGATE-EXPANSION-20250722

January umbrella names Stargate; Microsoft's January amendment explicitly accompanies Stargate; July Oracle agreement explicitly adds Stargate capacity. Do not automatically enroll every subsequent OpenAI contract. [S11, S12, S13]

### MSFT-OPENAI-PARTNERSHIP

**Kind:** SPECIFIC_BILATERAL_CONTRACT_LINEAGE.

**Exact member root IDs:**

- PBC-TECH-MSFT-OPENAI-20250121
- PBC-TECH-MSFT-OPENAI-20251028

Both revise the named Microsoft/OpenAI contractual relationship. October is a new definitive agreement and distinct root. January also belongs to Stargate's launch context. [S12, S14]

### US-GPU-EXPORT-APRIL2025

**Kind:** COMMON_EXTERNAL_POLICY_PROCESS.

**Exact member root IDs:**

- PBC-TECH-NVDA-H20-EXPORT-20250415
- PBC-TECH-AMD-MI308-EXPORT-20250416

Issuer-specific adverse charge disclosures arise from the same April U.S. advanced-GPU licensing policy episode. This is a common-shock sensitivity, not a supportive commercial program. [S15, S16]

### HPE-JUNIPER-ACQUISITION

**Kind:** SPECIFIC_TRANSACTION_AND_REGULATORY_LINEAGE.

**Exact member root IDs:**

- PBC-D-HPE-20250130-DOJ-CHALLENGE
- PBC-D-HPE-20250627-DOJ-SETTLEMENT

Challenge and settlement concern the same previously proposed acquisition. Distinct adverse and favorable milestones; retain the source publication date rather than parsing the settlement's ID. [S17, S18]

### LITE-FY2025-Q2

**Kind:** SAME_FISCAL_QUARTER_DISCLOSURE_CYCLE.

**Exact member root IDs:**

- PBC-C-LITE-20250203-PRELIMINARY
- PBC-C-LITE-20250206-EARNINGS

February 3 preliminary results explicitly point to February 6 full results. This is a disclosure-cycle family, not a cross-lane duplicate or two independent quarters. Preserve the preliminary/full distinction. [S19, S20]

## 3. Reject broad labels as common-program coarsening keys

These labels can remain descriptive metadata. They should not automatically remove distinct announcements or produce one synthetic event.

### US-AI-INFRASTRUCTURE

**Affected current root IDs:**

- PBC-TECH-MSFT-AI-CAPEX-20250103

Broad sector/geography theme. The Microsoft fiscal capex discussion does not establish a single shared announcement program with the other infrastructure plans.

### US-AI-MANUFACTURING

**Affected current root IDs:**

- PBC-TECH-NVDA-US-MANUFACTURING-20250414

Current row is already one NVIDIA-led umbrella announcement. Its broad label must not absorb unrelated issuer manufacturing announcements; use a unique root unless later same-project milestones are independently established.

### US-SEMICONDUCTOR-INVESTMENT-2025

**Affected current root IDs:**

- PBC-TECH-MU-US-EXPANSION-20250612
- PBC-TECH-TSM-US-EXPANSION-20250303

Different issuers, facilities and commitments. General U.S. semiconductor policy or administration endorsement does not establish one common transaction/launch. Do not add TXN's separate fabs plan.

### INTC-CAPITAL-2025

**Affected current root IDs:**

- PBC-TECH-INTC-ALTERA-20250414
- PBC-TECH-INTC-SOFTBANK-20250818
- PBC-TECH-INTC-USG-20250822
- PBC-TECH-NVDA-INTC-20250918

Shared issuer and financing objective, but different divestiture/equity counterparties and agreements. No source-backed single financing package connecting all four is established. Preserve as an issuer-financing dependence label only.

### OPENAI-INFRA-2025

**Affected current root IDs:**

- PBC-TECH-MSFT-OPENAI-20251028
- PBC-TECH-AMZN-OPENAI-20251103
- PBC-TECH-NVDA-OPENAI-20250922
- PBC-TECH-AMD-OPENAI-20251006
- PBC-TECH-AVGO-OPENAI-20251013
- PBC-TECH-ORCL-STARGATE-EXPANSION-20250722

Named common customer creates economic dependence; it does not establish one legal agreement, procurement round or announcement program. July Oracle belongs to the narrower Stargate family; October Microsoft belongs to its bilateral contract lineage. Retain the broad group only as a separately labeled common-customer sensitivity.

The repeated label **quarterly-earnings-calendar** must never collapse different issuers' earnings into one common program. The calendar arm exists to measure ordinary release clustering. Only the specific Lumentum fiscal-quarter linkage above qualifies as a shared disclosure cycle; deciding which first-result definition enters the deterministic audit remains the parent's separate calendar decision.

Also keep the following captured roots independent; no common program is established merely by their AI, domestic-investment, optical or power theme:

- PBC-D-IBM-20250428-US-INVESTMENT-PLAN
- PBC-D-TXN-20250618-US-FABS
- PBC-D-ETN-20250603-SIEMENS-ENERGY
- PBC-D-VRT-20250722-OKLO
- PBC-D-ANET-20250730-INDIA-PLAN
- PBC-D-LITE-20250807-US-CAPACITY
- PBC-D-CAT-20250821-HUNT-POWER

The tech one-member labels GOOG-ADTECH-LITIGATION, META-NUCLEAR, META-HYPERION, TSLA-25V170, AMD-CAPITAL-ALLOCATION and AMD-ZT-DIVESTITURE identify no multi-root family in these inputs. Preserve their roots individually. Do not broaden them using issuer name, industry or publicity alone.

## 4. Explicit handling of overlapping programs

### Preferred: multiple memberships, no transitive closure

Assign each canonical root a set of the accepted program IDs above. Keep one root row. A pair is directly related for a program-aware sequence sensitivity only when the two sets share an accepted ID. Suppress or mark that pair once, even if they share more than one ID. Do not duplicate events into one row per membership for event totals.

Do not take connected components of the entire root/program graph as if every connected event belonged to one program. The Apple–MP bridge does not establish that Apple's Corning agreement and MP's DoD transaction are one agreement or one coordinated launch. Likewise, Microsoft's January role does not make its October amendment part of the January Stargate launch or make all OpenAI contracts one program.

Exact overlapping memberships:

| Root ID | Accepted memberships |
|---|---|
| PBC-D-MP-20250715-APPLE-SUPPLY | APPLE-US-MANUFACTURING; MP-US-MAGNETS-2025 |
| PBC-TECH-MSFT-OPENAI-20250121 | STARGATE-US-BUILDOUT-2025; MSFT-OPENAI-PARTNERSHIP |

The Apple–MP link is stronger than a generic thematic inference: Apple places it inside its spending pledge, and MP explicitly relates the facility expansion to its DoD partnership. Its Apple supply is from Independence; the DoD package also includes the separately planned 10X facility. Shared supply-chain development does not make the facilities, contracts or financing interchangeable. [S2, S4, S5, S6]

This pair-marking sensitivity preserves event dates and economic stages. It differs from collapsing a full program's year of milestones into its first announcement and should be labeled accordingly.

### If a disjoint coarsened partition is required

Use the same exact memberships, with these explicit priority overrides before any outcomes are inspected:

- Assign PBC-D-MP-20250715-APPLE-SUPPLY to MP-US-MAGNETS-2025 for the disjoint partition. Apple's remaining partition members are its February and August aggregate spending roots.
- Assign PBC-TECH-MSFT-OPENAI-20250121 to STARGATE-US-BUILDOUT-2025. The October Microsoft amendment remains its own singleton in that partition.
- All other listed memberships are unambiguous. All unlisted roots retain their own root IDs as singleton keys.
- Preserve the complete memberships as metadata and report one alternative bridge assignment at a time: Apple–MP to Apple's program; Microsoft's January amendment to its bilateral lineage. Do not select the version that gives the stronger result.

These overrides favor the immediate, specifically linked launch/capacity program over the wider spending or bilateral-history umbrella. They are a declared deterministic convention, not a claim that the other membership is false.

If a partition is converted into synthetic events, use the earliest admitted source-date proxy among its members, retain every original date/stage/direction in the membership record, and explicitly call the estimand program-first-arrival. A year-long collapse discards genuine later economic milestones and is unsuitable as a silent replacement for ordinary event-arrival analysis. Group labels do not improve first-public timestamp certification or make UNKNOWN scheduling freely timed.

## Source links

- **S1:** [Apple February 24 U.S. pledge](https://www.apple.com/newsroom/2025/02/apple-will-spend-more-than-500-billion-usd-in-the-us-over-the-next-four-years/)
- **S2:** [Apple July 15 MP agreement](https://www.apple.com/newsroom/2025/07/apple-expands-us-supply-chain-with-500-million-usd-commitment/)
- **S3:** [Apple August 6 increase](https://www.apple.com/newsroom/2025/08/apple-increases-us-commitment-to-600-billion-usd-announces-ambitious-program/)
- **S4:** [MP July 10 DoD package](https://mpmaterials.com/news/mp-materials-announces-transformational-public-private-partnership-with-the-department-of-defense-to-accelerate-u-s-rare-earth-magnet-independence)
- **S5:** [MP July 15 Apple agreement](https://mpmaterials.com/news/mp-materials-and-apple-announce-500-million-partnership-to-produce-recycled-rare-earth-magnets-in-the-united-states/)
- **S6:** [MP July 16 offering](https://investors.mpmaterials.com/investor-news/news-details/2025/MP-Materials-Announces-Commencement-of-Proposed-500-Million-Public-Offering-of-Common-Stock/default.aspx)
- **S7:** [AWS/HUMAIN](https://press.aboutamazon.com/2025/5/aws-and-humain-announce-groundbreaking-ai-zone-to-accelerate-ai-adoption-in-saudi-arabia-and-globally)
- **S8:** [NVIDIA/HUMAIN](https://nvidianews.nvidia.com/news/humain-and-nvidia-announce-strategic-partnership-to-build-ai-factories-of-the-future-in-saudi-arabia)
- **S9:** [AMD/HUMAIN](https://ir.amd.com/news-events/press-releases/detail/1250/amd-and-humain-form-strategic-10b-collaboration-to-advance-global-ai)
- **S10:** [Cisco/HUMAIN](https://newsroom.cisco.com/c/r/newsroom/en/us/a/y2025/m05/cisco-expands-partnership-with-saudi-arabia-to-power-the-ai-future.html)
- **S11:** [Stargate January umbrella](https://openai.com/index/announcing-the-stargate-project/)
- **S12:** [Microsoft January amendment](https://blogs.microsoft.com/blog/2025/01/21/microsoft-and-openai-evolve-partnership-to-drive-the-next-phase-of-ai/)
- **S13:** [Stargate July Oracle expansion](https://openai.com/index/stargate-advances-with-partnership-with-oracle/)
- **S14:** [Microsoft October amendment](https://blogs.microsoft.com/blog/2025/10/28/the-next-chapter-of-the-microsoft-openai-partnership/)
- **S15:** [NVIDIA export-control disclosure](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000082/nvda-20250409.htm)
- **S16:** [AMD export-control disclosure](https://ir.amd.com/financial-information/sec-filings/content/0000002488-25-000039/amd-20250415.htm)
- **S17:** [DOJ HPE/Juniper challenge](https://www.justice.gov/opa/pr/justice-department-sues-block-hewlett-packard-enterprises-proposed-14-billion-acquisition)
- **S18:** [HPE/Juniper settlement](https://www.hpe.com/us/en/newsroom/press-release/2025/06/hpe-and-juniper-networks-reach-settlement-with-us-department-of-justice.html)
- **S19:** [Lumentum preliminary results](https://investor.lumentum.com/financial-news-releases/news-details/2025/Lumentum-Announces-Leadership-Transition/default.aspx)
- **S20:** [Lumentum full results](https://investor.lumentum.com/financial-news-releases/news-details/2025/Lumentum-Announces-Fiscal-Second-Quarter-2025-Financial-Results/default.aspx)

