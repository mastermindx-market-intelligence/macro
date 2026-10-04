# Finance global/regional source, basket and bilingual map — 23 September 2026

**Operation:** `gmi-finance-sector-research-20260923-sol-001`  
**Intended carrier:** Macro Draft/HOLD PR #7786  
**Prepared against:** `0b4f93ff27c74fa735744439ab741e7887db8ad8`  
**Protected procedure:** `mastermindx-market-intelligence/Mastermind@4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`  
**State:** NON-CANONICAL LOCAL RESEARCH MAP / PENDING SAME-CARRIER PERSISTENCE  
**Authority:** source planning and semantic design only. No source admission, entitlement grant, basket change, identity write, publication or trade authority.

## 0. Outcome

R9 must extend the existing international product rather than create a second global-Finance universe. The repository already has descriptive `intl_banks` and `intl_insurers` price surfaces. The Finance program should add owner-preserving semantic, economic and evidence overlays, not overwrite their live membership ledger or treat today’s curated composition as historical truth.

## 1. Existing repository surfaces

| Existing surface | Current job | Useful input | What it cannot prove |
|---|---|---|---|
| `data/baskets_intl/membership.json → intl_banks` | equal-weight descriptive non-US bank price surface | broad bank membership across Japan, UK, Europe, India, Korea and Australia | comparable bank economics, PIT history, local accounting/capital, direct theme identity or trade value |
| `data/baskets_intl/membership.json → intl_insurers` | broad insurers/diversified-financials surface | non-US insurers and selected diversified/market-infrastructure names | a coherent insurance business model; the basket mixes carriers, asset managers, exchanges and diversified firms |
| `site/basket_intl/**` | current member/price presentation | return, membership and existing basket workflow | company business-line evidence, local regulation, valuation anchor or causal relationship |
| `data/themes_intl/**` | international descriptive theme state | current descriptive stage/alerts | accepted global Finance ontology, cross-market causal transmission or stock selection |
| `intl_search` universe/cache | security and price discovery substrate | validated symbols in incumbent international universe | canonical legal-issuer/business identity or source rights for new fundamentals |

### 1.1 Existing membership law

- The international basket seeder is bootstrap-only.
- The live membership file is the ledger of record and accrues dated edits.
- Current long history is explicitly hindsight-curated/descriptive, not an out-of-sample membership history.
- A Finance research overlay may reference current basket membership but may not silently backfill it into historical evaluation.
- Any future basket change requires the incumbent basket owner and a separate accepted membership decision.

## 2. Selected architecture

```text
existing intl price/basket owners
        +
existing GMI identity/evidence/local-theme owners
        +
regional Finance research assertions
        +
accepted revisions/valuation/market owners
        ↓
owner-preserving regional Finance projection
```

Rejected:

- a second global security master;
- a second international basket database;
- a universal global bank/insurer score;
- one normalized capital ratio replacing local rules;
- one global financials theme that erases regional mechanisms;
- browser-time scraping or public static embedding of current full-fidelity research.

## 3. Regional source-owner matrix

| Region | System/regulatory sources | Company/statutory sources | Market/rail sources | Core refresh triggers |
|---|---|---|---|---|
| Euro area / EU | ECB Banking Supervision, EBA, ESMA, EIOPA, Eurostat, national regulators | issuer annual/interim reports; Pillar 3; SFCR | ECB payments, Euronext/Deutsche Börse/LSEG/clearing sources | results, Pillar 3, CRR/CRD/Solvency rule changes, stress tests, rate/sovereign regime |
| United Kingdom | Bank of England/PRA/FCA, ONS | issuer reports, Pillar 3, SFCR, ring-fenced entities | BoE payment statistics, LSEG, Pay.UK | MPC/rate, structural-hedge disclosures, redress/legal, PRA capital, results |
| Switzerland | FINMA, SNB | issuer reports and regulatory disclosures | SIX, payment/market sources | capital-rule decisions, integration milestones, wealth flows, results |
| Japan | BOJ, Japan FSA, Cabinet Office, statistics agencies | issuer annual/securities reports, integrated reports, solvency disclosures | JPX, BOJ payment/market statistics | BOJ normalization, JGB-purchase path, policy shares, ESR/ICS, results |
| Mainland China | PBOC, NFRA, CSRC, Ministry of Finance/NBS | A/H annual/interim reports, solvency disclosures, exchange filings | SSE/SZSE, CIPS/UnionPay where lawful, Stock Connect statistics | LPR/deposit rules, property/LGFV policy, C-ROSS, capital/dividend, results |
| Hong Kong | HKMA, Insurance Authority, SFC | HKEX issuer filings, insurer disclosures | HKEX/Connect, HKICL/FAST/FPS statistics | HIBOR/aggregate balance, RBC, Connect/listings, insurer free surplus, results |
| India | RBI, SEBI, IRDAI, NPCI, statistics agencies | issuer annual/quarterly reports and regulatory returns | NPCI UPI/IMPS, NSE/BSE, clearing/depository sources | deposit/credit, RBI prudential changes, UPI, unsecured credit, results |
| Singapore | MAS, statistics agencies | issuer reports/regulatory disclosures | SGX, FAST/PayNow/operator data | SGD rates, property/Greater China credit, wealth flows, exchange activity |
| Australia | APRA, RBA, ASIC, ABS | issuer annual/results; prudential disclosures | ASX, NPP/operator data | cash rate, mortgage/arrears, APRA capital/serviceability, results |
| South Korea | Bank of Korea, FSC/FSS | issuer/business reports, K-ICS disclosures | KRX, payment/settlement sources | household/real-estate PF, K-ICS, capital return, results |

## 4. Source-state vocabulary

- `PRIMARY_RETAINED_REVIEWED`
- `PRIMARY_OBSERVED_NOT_RETAINED`
- `PRIMARY_LOCATOR_PENDING`
- `SECONDARY_ATTRIBUTED`
- `RIGHTS_RESTRICTED`
- `DEFINITION_UNRESOLVED`
- `STALE_REVIEW_REQUIRED`
- `WITHDRAWN_OR_SUPERSEDED`
- `NOT_APPLICABLE`

A URL alone is not immutable retention. A search result is not source admission. Issuer-reported scale remains attributed until the review owner accepts it.

## 5. Regional semantic slices

These are research filters, not canonical themes or approved baskets.

| Slice | Region | Direct population | Economic mechanism | Existing price surface |
|---|---|---|---|---|
| euro_universal_banks | Euro area | diversified banks | ECB/sovereign/CRR3, commercial/CIB mix | partial through `intl_banks` |
| uk_domestic_banks | UK | ring-fenced retail/commercial banks | deposits, structural hedge, mortgage/consumer credit, conduct | partial through `intl_banks` |
| swiss_wealth_banks | Switzerland | wealth-led banks | net new money, cash/fee mix, integration and capital | partial through `intl_banks` |
| european_composite_insurers | Europe | P&C/life/asset-management groups | IFRS17, Solvency II, underwriting/life/fees | partial through `intl_insurers` |
| global_reinsurers_europe | Europe/Bermuda adjacency | reinsurers | rate/terms, reserve/cat/capital | partial through `intl_insurers` |
| european_market_infrastructure | Europe/UK | exchanges/data/clearing | activity, subscriptions, indices, clearing | mixed into `intl_insurers`; analytically separate |
| japan_megabanks | Japan | MUFG/SMFG/Mizuho cohort | BOJ, yen spread, JGB duration, policy shares | partial through `intl_banks` |
| japan_insurers | Japan | P&C/life groups | ESR/ICS, rates, policy shares, global underwriting | partial through `intl_insurers` |
| japan_brokers_exchange | Japan | Nomura/JPX-like | wealth/markets, volume/data | no clean current basket |
| china_state_banks | Mainland China | state-controlled banks | policy credit, NIM, property/LGFV, capital/dividend | partial through other China surfaces; not one approved Finance basket |
| china_retail_wealth_banks | Mainland China | retail/private-bank franchises | deposits, wealth, cards, credit quality | not cleanly isolated |
| china_hk_life_insurance | China/HK | life insurers | VONB, EV/CSM/free surplus, solvency | partial through `intl_insurers` |
| hong_kong_financial_infrastructure | Hong Kong | HKEX/Connect/clearing | cross-border volume, listings, data, HIBOR | no clean current basket |
| india_private_banks | India | private banks | deposits/CASA, credit/vintage, capital | partial through `intl_banks` |
| india_nbfcs | India | consumer/specialty nonbanks | funding, risk-adjusted yield, vintages | not cleanly isolated |
| india_payment_rails | India | UPI/issuer/acquirer/processors | count/value/adoption to monetization | infrastructure semantic slice; not automatically public-equity basket |
| singapore_wealth_banks | Singapore | regional banks | wealth/transaction/deposits/Greater China | partial through `intl_banks` |
| australia_mortgage_banks | Australia | major banks | mortgages, deposits, APRA capital, franking | partial through `intl_banks` |
| korea_financial_groups | Korea | bank/card/securities/insurance holdings | household/PF credit, nonbank mix, K-ICS | partial through `intl_banks`/`intl_insurers` |
| asian_exchanges_derivatives | Japan/HK/SG/AU/KR | market infrastructures | volume/RPC/data/listing/clearing | no coherent approved basket |

## 6. Candidate basket admission gates

A regional semantic slice may become an approved price basket only after:

1. exact economic mechanism;
2. issuer/business/security identity;
3. direct/diversified/enabler/proxy/disrupted role;
4. measured exposure or honest not-disclosed state;
5. local accounting/regulatory compatibility;
6. point-in-time membership history or explicit current-membership caveat;
7. listing/currency/FX/ADR treatment;
8. liquidity/data/rights coverage;
9. overlap and double-counting analysis;
10. transparent weighting and rebalance rule;
11. correct local and global benchmark;
12. owner acceptance and evidence receipt.

Do not pad small regional cohorts with weak proxies. A cross-listed security appears once per declared basket identity rule, not once per ticker string.

## 7. Proposed product routes and joins

- Theme Tracker remains a router and does not become a world-Finance graph.
- The existing international page/basket routes remain the price/membership surfaces.
- The primary Finance dossier gains a `Global & Regional Systems` module.
- Region dossier routes should follow existing stable regional route owners rather than creating another microsite family.
- Company/business views join through accepted legal-issuer/security identity.
- A regional assertion without a validated listing may display attributed company evidence but cannot inherit stock price, valuation or portfolio relevance.
- The evidence drawer remains authenticated/private/no-store for current full-fidelity research.

## 8. EN/ZH controlled glossary

| English | 中文 |
|---|---|
| Finance system | 金融体系 |
| financial institution | 金融机构 |
| legal issuer | 法律发行人 |
| listed security | 上市证券 |
| share class | 股份类别 |
| depositary receipt | 存托凭证 |
| dual listing | 双重上市 |
| A-share | A股 |
| H-share | H股 |
| reporting currency | 报告货币 |
| functional currency | 功能货币 |
| constant currency | 固定汇率 |
| foreign-exchange translation | 外汇折算 |
| universal bank | 综合银行 |
| retail bank | 零售银行 |
| commercial bank | 商业银行 |
| investment bank | 投资银行 |
| deposit franchise | 存款基础 |
| structural hedge | 结构性对冲 |
| net interest income | 净利息收入 |
| net interest margin | 净息差 |
| deposit beta | 存款贝塔 |
| tangible book value per share | 每股有形账面价值 |
| return on tangible equity | 有形股本回报率 |
| common equity tier 1 | 普通股一级资本 |
| risk-weighted assets | 风险加权资产 |
| total loss-absorbing capacity | 总损失吸收能力 |
| minimum requirement for own funds and eligible liabilities | 自有资金及合格负债最低要求 |
| liquidity coverage ratio | 流动性覆盖率 |
| net stable funding ratio | 净稳定资金率 |
| expected credit loss | 预期信用损失 |
| Stage 2 assets | 第二阶段资产 |
| Stage 3 assets | 第三阶段资产 |
| non-performing loan | 不良贷款 |
| special-mention loan | 关注类贷款 |
| gross NPA | 总不良资产 |
| net NPA | 净不良资产 |
| slippage | 新增不良 |
| charge-off | 核销 |
| recovery | 收回 |
| provision | 拨备费用 |
| allowance | 损失准备 |
| provision coverage ratio | 拨备覆盖率 |
| policy-directed lending | 政策性信贷 |
| local-government financing vehicle | 地方政府融资平台 |
| priority-sector lending | 优先领域贷款 |
| policy shareholding | 政策持股/交叉持股 |
| asset under management | 管理资产 |
| assets under administration | 管理服务资产 |
| fee-paying assets | 收费资产 |
| net new money | 净新增资金 |
| client assets | 客户资产 |
| contractual service margin | 合同服务边际 |
| value of new business | 新业务价值 |
| embedded value | 内含价值 |
| free surplus | 自由盈余 |
| solvency ratio | 偿付能力充足率 |
| current accident year | 当年事故年度 |
| prior-year development | 往年准备金发展 |
| combined ratio | 综合成本率 |
| reinsurance | 再保险 |
| risk-adjusted rate | 风险调整后费率 |
| market infrastructure | 金融市场基础设施 |
| central counterparty | 中央对手方 |
| clearing | 清算 |
| settlement | 结算 |
| custody | 托管 |
| market data | 市场数据 |
| Stock Connect | 沪深港通 |
| northbound flow | 北向资金 |
| southbound flow | 南向资金 |
| average daily turnover | 日均成交额 |
| open interest | 未平仓合约 |
| rate per contract | 每合约费率 |
| Unified Payments Interface | 统一支付接口 |
| real-time payment | 实时支付 |
| capital return | 资本回馈 |
| share buyback | 股份回购 |
| franking credit | 股息抵税额 |
| state ownership | 国有持股 |
| policy mandate | 政策职能 |
| currency board | 联系汇率制度 |
| required return | 必要回报率 |
| rerating | 估值重估 |
| de-rating | 估值下调 |
| price recognition | 价格确认 |
| point-in-time | 时点一致 |
| comparison refusal | 拒绝比较 |

### 8.1 Copy law

- Chinese copy preserves the technical distinction; it is not shortened into a broader everyday term when that changes meaning.
- Acronyms such as CET1, RWA, IFRS 17, CSM, VONB, EV, NIM, NPL, UPI and CCP remain visible with Chinese explanation.
- `rerating` is rendered as `估值重估`; it does not imply a guaranteed rise.
- `de-rating` is `估值下调`; it is a valuation state, not automatically a sell instruction.
- `policy support` is `政策支持`; it is not `政府担保` unless a legal guarantee exists.
- `state-owned` is `国有控股/国有持股` according to actual control; it is not a quality label.
- `free surplus` in insurance is `自由盈余`, not generic free cash flow.
- `structural hedge` is `结构性对冲`; it must include its bank-specific deposit/reinvestment context.
- A/H/ADR labels remain explicit in both languages.

## 9. Refresh and review cadence

| Observation | Minimum trigger | Additional trigger |
|---|---|---|
| company financial/capital metrics | annual/interim/quarterly result | restatement, acquisition, capital action, regulator filing |
| regulatory capital/rules | regulator publication/effective date | consultation finalization, transition step, stress test |
| central-bank/rate mechanism | scheduled decision/statistics | emergency operation or regime change |
| payment/rail statistics | monthly/quarterly operator release | rule/fee/access change |
| exchange/Connect activity | daily/monthly/annual owner data as admitted | new product, outage, rule/quota change |
| insurance solvency/VONB/EV | issuer/regulator reporting cycle | assumption review, catastrophe, capital action |
| basket membership | incumbent owner’s dated change | corporate action, delisting, identity correction |
| source review | source-family SLA | rights, definition or correction invalidator |

## 10. Rights and publication boundaries

- Public regulatory and issuer sources still require source-family review, locator and retention state.
- Exchange/rail statistics may have terms restricting redistribution of detailed current payloads.
- Research Vault and paid institutional research remain separate rights families.
- Current detailed assertion bodies remain authenticated/private unless the publisher owner approves a deliberately reduced public example.
- No current full-fidelity payload enters `site/**`, public Git seeds, localStorage, IndexedDB or service-worker caches.
- The international basket membership file remains product data owned by its incumbent path; research documents do not grant permission to mutate it.

## 11. International evaluation boundary

Historical evaluation must preserve:

- contemporaneous regional membership;
- listing and currency identity;
- accounting/regulatory regime version;
- source publication and availability;
- local market holidays and settlement;
- local and base-currency returns;
- dividends, withholding and corporate actions;
- A/H/ADR conversion and cross-listing changes;
- controls for rates, sovereign, currency and local market beta;
- mergers, privatizations, delistings and state interventions.

Current curated `intl_banks` or `intl_insurers` membership may be used only as explicitly non-PIT descriptive context until history is proven.

## 12. Exact next actions

1. Serialize the 28-record R9 research packet.
2. Bind exact locators for held records where public primary evidence permits.
3. Build the R9 checkpoint with artifact hashes and unresolveds.
4. In a write-capable surface, persist the same bytes to PR #7786 after reconciling its then-current head.
5. Begin R10 only after R9 is durably reconciled.

## 13. Non-claims

This map does not admit any source, change any international basket, create a global Finance theme, validate any bilingual product copy, establish an entitlement, or authorize implementation.