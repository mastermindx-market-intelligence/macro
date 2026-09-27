# Catalyst Intelligence R11 — economic exposure before stock selection

**Historical research and an interactive design specimen, not a production connection or recommendation.** This extends the existing #8061 source proposal, unified workspace contract and #6712 programme. It does not add a new rights registry, royalty engine, identity service, ranker, collector or execution authority.

Protected procedure: Mastermind `fda6ed3911cdda24eb63b2ccbe1b174121cf404f`, INDEX `94d1af402598894372858793a5b1931019c5fa77`, compatible Skillpack 1.0.1/bootstrap 1. Code-inspection basis: Macro `7742e50824440ee5a8863360dedf54e3102dfb55`. Direct design/research retained for principal judgment and lower total overhead; no worker or watcher started.

## 1. The investment error this closes

A drug, trial sponsor, current listed security, commercial operator and cash-flow beneficiary are different identities. A successful catalyst can produce very different shareholder payoffs. The analyst cannot select the right stock by finding a ticker beside the drug name.

R11's **Who benefits?** view sits inside the existing Cobenfy research case. The reader receives the conclusion first: one medicine creates three different exposures. A controlled annual-sales illustration then explains the royalty split. Source inspectors and builder annotations are deeper in the same workflow, not another application. The original twelve synthetic candidates and their independent specialist engines remain unchanged; BMY, RPRX and PRTC are not promoted into real ranked picks.

This is not a retreat from recommendations. Correct retained economics are a prerequisite to comparing catalyst-driven equity returns and determining which security best expresses a thesis.

## 2. Primary-source findings and their dates

The companion `CATALYST_INTELLIGENCE_COBENFY_ECONOMIC_EXPOSURE.json` preserves four primary URLs, locators, limitations and source-reported identities. Scope is historical documents through 30 April 2025, reviewed now; it is not an as-of pipeline reconstruction or a current investment opinion.

- BMS's 18 March 2024 acquisition-close announcement says Karuna became wholly owned and its shares ceased trading. A former sponsor symbol must not silently become a current investment candidate.
- Royalty Pharma's SEC 8-K signed 27 September 2024 describes 3% of annual sales through $2bn and 1% above. It also identifies the $25m approval milestone payable by Royalty Pharma to PureTech.
- PureTech's 30 April 2025 FY2024 report describes its retained approximately 2% share above the sales threshold. Detailed Note 18 expresses the structure as all royalties through $60m annually going to Royalty Pharma, then a 33%/67% split of excess royalties. Preserve both original formulations; the simplified headline percentages are not precision-grade legal valuation.
- PureTech recognized $315k in FY2024 royalty revenue and reported forwarding $315k to Royalty Pharma in Q1 2025. The illustration's zero retained on those receipts is after that transfer, not zero FY2024 revenue, same-period cash flow, total company income or lifetime transaction proceeds.
- Separate approval milestones were $4m from BMS and $25m from Royalty Pharma. A summary paragraph attributes the latter to BMS, whereas detailed Note 18 and Royalty Pharma's 8-K identify Royalty Pharma. The discrepancy stays visible. The upfront royalty sale and milestones must not be added to a recurring royalty rate.
- The BMS FY2024 Form 10-K adds acquisition/financing context. Historical acquisition consideration is not a current fair-value estimate. Its exact filing date was not extracted; the record does not invent one.

The underlying source documents were not byte-archived; production first-observed clocks, canonical securities, dated legal rights and full agreements remain unverified. The reported $315k is not reverse-engineered into an undisclosed exact sales figure from BMS's rounded launch-sales disclosure.

## 3. A bounded, useful illustration

For assumed **qualifying annual net sales** S in USD millions, the view uses the simplified disclosures:

- disclosed pool = 0.03 × S;
- Royalty Pharma = 0.03 × min(S, 2000) + 0.01 × max(S − 2000, 0);
- PureTech retained = approximately 0.02 × max(S − 2000, 0).

At $3bn, the illustrative pool is $90m, split about $70m/$20m. These are portions of the same pool, not $180m of economic benefit. At $2bn, the displayed split is $60m/$0. Thresholds apply marginally and annually; they do not reset all prior sales to the lower rate. Zero sales produce no sales royalty.

The slider and presets never change trial likelihood or create a stock stance. The export keeps the selected input, source evidence, approximations and all unprovided investment fields. Tax, lags, territory exceptions, term expiry, amendments, other obligations and discounted value are unmodeled. BMS's remaining revenue is not operating profit. This browser illustration must not become a parallel production financial engine.

## 4. Concrete existing backend interfaces located

| Existing source | Exact observed interface and scope | What is not proved |
|---|---|---|
| `engine/intelligence_workspace/entity.py`, blob `5303d211a830bc84650b7934dd906cb2d30005a0` | `DataOSIdentityNormalizer.normalize_many` consumes the existing security master and vendor aliases; no identifier minting. Current-symbol input is marked `current_alias_only`. | Historical asset/right ownership or an executed BMY/RPRX/PRTC identity result. |
| `engine/neuralweb/company_intelligence_reader.py`, blob `47fe7d411434ba9ad321bf825edcf380aabc8e5c` | `read_event_workspace` requires a canonical event ID or published alias and verifies marker, immutable manifest, byte count, hash and event identity. | A published Cobenfy/BMY event binding, actual object availability, permission expansion or recommendation authority. |
| `engine/intelligence_workspace/adapters/company_intelligence.py`, blob `ef3994d5adbec223b5fe2dc14b304776eff3758e` | `CompanyIntelligenceAdapter.resolve_many` consumes latest-event metrics and preserves stale/missing/lineage states. | A complete drug dossier, territorial license graph or retained-cash-flow model. |

The full workspace reader is a real source interface, distinct from the limited public teaser, but it remains context-only. A current security alias is not a historical legal entitlement. No missing search result is evidence that the relevant capability is globally absent.

The attempted live qualification did not return a usable owner result. The M1 canonical-checkout data path was explicitly outside that connector's allowed roots; the compound M1 source introspection was platform-blocked before dispatch. Neither was retried or rerouted. Public endpoint/manifest attempts yielded no verified object; the Firecrawl public-endpoint attempt stopped for insufficient credits. No credentials, subscriptions, source paths or egress checks were changed. Repository source inspection is the verified result; runtime connection is not.

## 5. Exact next vertical through incumbent owners

1. Through an already permitted owner runtime or approved repository-data access, obtain the actual security IDs and alias validity intervals. Resolve listing venue/currency/share class and retired securities; do not construct SEC IDs from display symbols.
2. Bind the drug/product and each legal beneficiary through the existing identity/GMI/economic-rights owner. Retain effective dates, territory, indication, royalty tier, milestone versus sales cash flow, transfer obligations and source lineage. A tradeable parent and its license subsidiary must remain distinguishable.
3. Obtain a real published event/alias and exact immutable reader receipt. Pass the corresponding authorized facts to the research and financial owners without promoting context-only objects into signals.
4. Reconcile retained cash flows, pass-through liabilities, tax, royalty duration, funding and diluted shares through existing financial interfaces. Prevent the same royalty from being capitalized once as gross receipts and again as retained proceeds. A recorded financing liability and its projected payments also need a consistent valuation treatment, not automatic double subtraction.
5. Evaluate clinical/commercial scenarios, common-driver correlations and security-specific equity values. Compare each issuer's payoff against its own price/valuation and existing policy, not its gross sales exposure. Only an accepted calibrated model and recommendation owner can admit a real pick.
6. Freeze prospective forecasts and evaluate realized outcomes. This already-approved historical drug is a contract/research case, not a claimed successful prediction.

For Defense, the analogous distinction is prime award versus subcontract, teaming share, supplier content, retained margin and delivery obligation. Share the identity/economics discipline, not a clinical prior or a universal probability. Themes must not count several securities exposed to the same product or exclusive award as independent bets.

Corresponding acceptance extends the existing SC-08/12/13/19/27/28 obligations: retired symbol refusal; dated legal-right binding; native tier preservation; pass-through versus retained economics; milestone/cash/accrual separation; no double counting; and no future/current-source substitution. A missing right withdraws only the dependent investment estimate while source facts remain inspectable.

## 6. Final local proof and limits

Final HTML SHA-256: `c0ed3633fd2b719a241d8e747aae86cdfa9a8b3714af002b90e6d217bced74fb`.

- `R11_VALIDATION.json`: 122 passed / 0 failed. Actual controls, annual tiers, source-native terms, invalid inputs, mass conservation, source dialogs, exports, no fabricated identities, original candidate preservation and dark/light layouts at 1440/768/390/320.
- `R11_R10_COMPATIBILITY.json`: the existing R10 suite rerun against these exact R11 bytes, 180 passed / 0 failed.
- `R11_VISUAL_SEMANTICS.json`: 3 passed / 0 failed after two visually identified defects failed first: the inherited synthetic footer on real research and zero-sales copy implying a positive flow.
- Six feature-presence checks distinguish the new view from R10; they are structure evidence, not financial-model validation.
- Twenty final captures cover exposure, threshold, source inspector, builder notes and first view at 1440/390 in both themes. Representative desktop/mobile and threshold views were inspected. Browser tests recorded no uncaught exceptions or network requests.

All rendering uses the established isolated Chromium `set_content` path. The older file-navigation refusal was not retried. Actual file-open/reload, production routes, live source readers, full legal/source corpus, calibrated forecasts, Chinese parity and independent human design acceptance remain unproved. Test counts are repeated UI/fixture assertions, not investment performance. Final visual review also caught an unstyled original-source link below the 44px target: a failing regression preceded reuse of the shared button class; the final suite includes both source-open and source-close target checks. Capture scroll was explicitly settled before first-view images; this is screenshot methodology, not a product repair.

## 7. Native Paper and source adoption

No R11 Paper content, focus or working-indicator effects. The previous file reservation still has no consumed release. A new existing-owner #927 report, comment `5852584024`, additionally says Paper 0.5.12 now advertises catalog `8cd27488a3adfc19c6c36d4349b75feebc71c159253c47f8a0f8d50c27043deb` rather than reviewed `ca90a537ee97f3e371ac945a8a3b9a928ba7fac9ffaeb67e31491075a0790570`, with `accepted_for_write:false`. This turn consumed that report; it did not independently rerun catalog qualification. Preserve the blocked `rename_pages` action and let the existing runtime/source owner qualify the change. Do not repeat the earlier successful nine-gateway rollout or weaken the guard.

Native continuation remains file `01M2WGNCX9475G79JRKJTCM08P`, Bio page `p-K-0`, desk `1ECU-0`, content `1EJZ-0`. After actual file-window admission and catalog qualification, author the unified front door and specialist depth on those targets and inspect actual Paper screenshots. This HTML is supporting work, not native completion.

Keep the same #8061 branch and Draft/HOLD-for-Sol until exact-source independent review and applicable integration gates pass. No review was returned in this turn's bounded check. Source publication is not default-branch adoption or a validated engine. Current mode may be retained; no mode switch repairs a permission, catalog or custody boundary.
