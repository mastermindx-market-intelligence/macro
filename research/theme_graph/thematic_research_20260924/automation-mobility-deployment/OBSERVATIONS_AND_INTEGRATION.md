# GMI C — observations and integration proposal

Operation: `gmi-theme-research-automation-mobility-deployment-20260924-001`  
Parent: Macro #7886  
Child: Draft/HOLD #7893  
Status: RESEARCH/DESIGN PROPOSAL — complete for review with C-R1–C-R4 corrections; no observation is enrolled, no interface is live, and no new ingestion/evidence/graph/store/scheduler is authorized. C-O4/C-O5 are supplemental preliminary profiles, not fully qualified acquisition/cadence contracts.

## 1. User and machine job

The investor question is not “is this company associated with automation?” It is:

> Has a demonstrated capability crossed into useful, paid, economically retained deployment, and which observation would prove or falsify the next step?

The machine must therefore keep these stages independently observable:

`catalog/demo → contract/financing → installation → accepted operation → productive unit → customer benefit → supplier/operator revenue → support/capital/financing → retained cash`.

A record may legitimately stop at any stage. Missing downstream fields remain missing; the UI should explain the broken link rather than infer a green completion state.

## 2. Information clocks and correction behavior

Every admitted future observation should preserve, through existing owners:
- source publication/availability;
- first system observation where known;
- business/event effective interval;
- measurement period;
- definition/version;
- unit and currency;
- source lineage/independence;
- correction/supersession lineage;
- ownership/economic perimeter.

A later corrected stall count, operational-system count or tonnage total must not overwrite the as-known earlier value in historical evaluation. A contractual target is not an achieved operating observation. A date-only source cannot establish intraday ordering. A deterministic ratio derived from one source is dependent on that source and must not be counted as a second confirmation.

C-R1–C-R3 additionally require the measured-versus-prospective status, scheduled-versus-available rate denominator, integrated exposure interval, recognition-versus-collection basis, and accounting-profit-versus-cash-investment perimeter. Correcting any of these invalidates affected derived numbers AND prose; it does not invalidate unaffected source observations.

## 3. Observation profile C-O1 — warehouse productive utilization and buyer payback

**User question.** Has a warehouse-automation installation progressed from deployment revenue into reliable productive work that creates customer value and recurring supplier economics?

**Population.** One explicitly identified site or a comparable site cohort using the same system generation, customer job, acceptance definition and operating period. Do not mix regional DCs, e-commerce FCs, store-backroom systems and different automation generations.

**Exact observables.**
- accepted/commissioned system-days;
- available system-hours and downtime by defined cause;
- pallets/cases/eaches or other accepted workload completed;
- exception/recovery events;
- onsite and remote intervention labor-hours;
- maintenance/spares/warranty burden;
- software/support/operations-service fees;
- customer labor and relevant avoided/added operating cost;
- installed capital and integration spend;
- supplier recognized revenue and cost under the matching contract/cohort.

**Numerators / denominators.**
- availability = available scheduled system-hours / scheduled system-hours;
- productive throughput = accepted workload / available or scheduled system-hour, with the chosen denominator retained;
- intervention intensity = human intervention-hours / accepted workload or system-hour;
- customer labor intensity = customer labor-hours / accepted workload;
- operating-cost intensity = matched operating cost / accepted workload;
- buyer cash return requires attributable avoided/additional cash against the SAME installation/cohort divided by full attributable investment. Do not use corporate capex or consolidated savings as a site denominator. State whether the cash numerator is before or after investment/financing, retain the horizon and investment basis, and do not treat one period's ratio as lifetime ROI. In a cash bridge, add back included noncash depreciation before subtracting cash capex once; keep taxes, working capital and financing on their declared basis rather than subtracting depreciation and investment twice.

**Existing evidence.** Symbotic provides system-in-deployment, operational-system and revenue-category cohorts; Walmart provides broad network automation/productivity evidence. The inspected public sources do not provide a matched Symbotic site payback cohort.

**Source/acquisition feasibility.**
- public issuer filings/releases: feasible for deployment counts, revenue categories and some customer statements;
- exact site operating metrics: potentially customer/vendor case studies or entitled operational data; current availability unknown;
- contract/site capex: may be private and remain unavailable.

**Cadence.**
- deployment/contract/financial events: event-driven and earnings/filing releases;
- site operating observations: native operational cadence if lawfully available, with monthly/quarterly review aggregation rather than narrative regeneration.

**Business horizon.** Commissioning through at least a stabilized operating cohort; compare ramp separately from mature operation.

**Retention/correction.** Retain site/system generation, prior metric vintages, customer acceptance definition and any corrected deployment/operational-system counts.

**Strongest alternative.** Supplier revenue is driven by construction progress and a concentrated rollout while mature site utilization or buyer ROI remains weaker/unknown.

**Falsifier of the productive-payback thesis.** A matched mature cohort shows persistently low availability/throughput, rising intervention/support cost, or no evidence that attributable customer benefit clears full capital/operating burden.

**Existing intended owners.** GMI evidence/relationship owner for source-scoped claims; existing financial/Earnings owner for recognized revenue/cost; Data OS/identity for site/company/security bindings; existing Research Vault/private publication owner where permitted; existing F04/shared dossier composition for eventual presentation.

**Currently unmeasurable.** Symbotic-attributable Walmart site ROI, exact intervention labor, and full installation capital in the inspected public corpus.

## 4. Observation profile C-O2 — charging site/vintage economics

**User question.** Is charger-network growth producing reliably available, paid energy throughput and acceptable site economics, rather than merely more installed ports?

**Population.** Same network ownership model, site vintage, geography/utility territory, charger class/power and operating period. Separate owned public network, eXtend/third-party assets, fleet/private assets and OEM-funded cohorts. The retained 99 GWh source metric is PUBLIC-network throughput; C-R2 concerns exposure timing/averaging, not a public-versus-AV/eXtend population error.

**Exact observables.**
- operational stalls/ports, commissioning/retirement dates and integrated eligible stall-hours/days;
- actual availability, not contractual threshold;
- sessions and observed delivered kWh;
- realized direct charging revenue and recognition/collection period, separated from regulatory credits and non-energy network/OEM fees;
- energy commodity and demand charges;
- host rent/revenue share and network/site fees;
- maintenance/repair/field-service cost;
- separately scoped cash capital expenditures, OEM/grant/funding offsets and accounting depreciation;
- operating working-capital/timing changes, cash taxes and other noncash adjustments when required by the selected cash measure;
- debt/subsidy attribution, cash interest, principal repayment and new borrowing on a separately named financing view;
- retirement/replacement events and the issuer's averaging/eligibility definition.

**Numerators / denominators and C-R1–C-R2 measurement logic.**
- measured direct charging revenue: `R_charge = sum(E_i * p_i)`, where E_i is observed kWh and p_i compatible realized net currency/kWh for the same contract/customer/period cell. No additional stall count or availability factor is applied. Recognition/timing and non-energy adjustments require an explicit reconciliation; this is not automatically cash collected;
- prospective energy: `E_hat = sum(H_i * a_i * q_i)` where H_i is scheduled eligible stall-hours, a_i available/scheduled fraction and q_i kWh per AVAILABLE stall-hour; all cells and periods must match;
- a rate q_sched_i per ALL scheduled eligible stall-hours already incorporates availability: `E_hat = sum(H_i * q_sched_i)`, without a_i;
- energy per scheduled eligible stall-day = observed kWh / integrated eligible stall-days. Energy per available stall-hour = observed kWh / available stall-hours. These are different rate bases, not interchangeable denominators;
- session utilization = sessions / integrated eligible stall-days;
- realized charging yield = matched direct charging revenue / matched delivered kWh. An aggregate quotient is not a measured site tariff, and a yield derived from revenue supplies no independent confirmation of the same revenue;
- energy/site cost intensity = (matched energy cost + matched site operating cost) / matched delivered kWh;
- contribution intensity = matching charging contribution / matched delivered kWh, with included costs and accounting/cash status explicit;
- an end-quarter count times all quarter days is not integrated exposure. `3930 * 276 * 91 = 98,705,880 kWh` remains a hypothetical endpoint approximation, not a reconciliation to 99 GWh. Actual comparable exposure and averaging definition remain unmeasured here. No causal expansion attribution or mature-site return follows from numerical closeness.

**C-R3 profit and cash scopes.** Preserve reported accounting categories rather than subtracting group depreciation or group capex from a network margin without reconciliation. On a matched explanatory perimeter, operating profit = recognized revenue − accrued operating costs excluding D&A − D&A. Cash capex does not appear as a second depreciation charge. A separate post-tax/post-investment/pre-financing bridge adds back included D&A and other identified noncash items, reconciles operating working capital/timing, and deducts cash taxes and cash capex once. Starting from a cash measure that already includes a cost/tax/interest or working-capital adjustment does not permit deducting it again. Financing and restricted cash remain separate; a capital cash offset appears only once, using either gross capex plus a separately qualified receipt or the matching net-investment definition. Unknown inputs stay unknown.

A site cash-return measure must name its numerator (before/after investment and financing), sponsor-capital denominator, horizon and matching site/vintage; it is not interchangeable with accounting gross margin or automatically a lifetime return. The SYNTHESIS C-R3 example is a synthetic reconciliation, not an estimate of undisclosed EVgo cash flows.

**Existing evidence.** EVgo Q2 2026 reports 3,930 public-network stalls at quarter end, 276 kWh/day average daily public-stall throughput, 99 GWh public-network throughput, charging-network revenue/cost, capex offsets and DOE financing. Its GM contract defines 97%/95% availability thresholds, but the inspected filing does not establish achieved availability. These existing reported observations are preserved; the current repair does not acquire a new operating series or validate the issuer's average denominator.

**Source/acquisition feasibility.**
- public filings/releases: feasible for portfolio throughput, revenue/cost, capex/funding and contractual terms;
- charger status/actual uptime: potentially public/entitled network data, but source definition and history must be qualified;
- utility tariff/demand charges: generally public by tariff but site mapping can be difficult;
- host economics/site capex: often private or aggregated;
- integrated historical stall exposure and averaging/eligibility rules: not qualified in this repair; do not derive them from endpoint closeness.

**Cadence.**
- charging activity/availability: event or operational cadence where entitled;
- commissioning/retirement and eligibility changes: retain event intervals for the period denominator;
- tariff/funding/contract changes: event-driven;
- financial reconciliation: quarterly;
- structural site-vintage review: quarterly or semiannual.

**Business horizon.** Site ramp through mature utilization and asset replacement; financing horizon should match debt/subsidy obligations.

**Retention/correction.** Preserve station/stall identity, site vintage, commissioning/retirement intervals, denominator/rate basis, availability-definition version, tariff vintage, funding attribution and corrected energy/session data. A correction to exposure may change a derived intensity without changing the independently observed energy total.

**Strongest alternative.** New sites may dilute aggregate per-stall utilization during ramp even while mature-site economics remain sound; portfolio-level decline therefore does not prove deterioration. Cohort weighting, availability and mature demand can also differ. Their contributions are not identified by the endpoint calculation.

**Falsifier of a scale-to-return thesis.** Mature matched cohorts fail to raise/hold delivered-energy utilization or site contribution after availability, power, rent and maintenance are measured, and after accounting profit and cash investment are evaluated on separate complete bases.

**Existing intended owners.** Energy for power/tariff/grid semantics; financial owner for revenue/cost/capex/debt; GMI for source-local relation and thesis; identity for station/operator/company bindings; existing evaluation owner for any future prospective study.

**Currently unmeasurable.** Publicly matched EVgo site-level uptime, integrated eligible exposure/average definition, tariff, host economics, selected site cash-flow adjustments and full site return. No missing input is replaced by zero or by a synthetic fixture.

## 5. Observation profile C-O3 — autonomous quarry cost per accepted ton

**User question.** Has an autonomous haulage system created reliable paid productive work at lower or strategically acceptable full cost than the staffed alternative?

**Population.** Exact quarry/site, vehicle model, autonomy system/version, shift pattern, route/haul profile and operating interval. Bull Run should not be pooled with different mines/quarries without normalization.

**Exact observables.**
- go-live and acceptance date;
- scheduled and available truck-hours;
- tons hauled and accepted destination/quality definition;
- cycles, distance and route profile where useful;
- autonomous versus manual/recovery mode;
- remote/on-site supervision and intervention hours;
- maintenance/downtime and consumables/fuel;
- vehicle + autonomy + dealer/integration capital;
- software/support/dealer fees;
- staffed baseline operator labor and comparable productivity;
- contract revenue and supplier/dealer cost where disclosed.

**Numerators / denominators.**
- productive rate = accepted tons / available truck-hour;
- availability = available scheduled truck-hours / scheduled truck-hours;
- intervention intensity = intervention/supervision hours / operating truck-hour or accepted ton;
- full cost per accepted ton = (matched labor + fuel + maintenance + software/support + depreciation/capital charge + other attributable cost) / accepted tons. All numerator terms are costs on the same currency/period/perimeter. Declare an accounting-cost or explicitly modelled lifecycle-cost basis; do not add cash asset purchases on top of a depreciation/capital charge for the same investment. A cash-investment view is separate and follows C-R3, with tax, working-capital and financing scope explicit where included.

**Existing evidence.** Caterpillar reports Bull Run go-live in November 2024, productivity matching staffed machines shortly after go-live, more than 2m tons in the first year and more than 3.5m tons after 18+ months, followed by expansion to two additional Virginia sites. Caterpillar/Carter Machinery also report embedded implementation/support and training.

**Source/acquisition feasibility.**
- vendor/customer releases: feasible for milestones, tonnage and expansion;
- detailed operational telemetry: may require customer/dealer entitlement;
- contract price, full support cost and labor baseline: not disclosed in inspected public sources.

**Cadence.**
- operational metrics: shift/day/month where entitled;
- expansion/contract and fleet changes: event-driven;
- financial reconciliation: quarterly/annual where supplier/customer reporting permits.

**Business horizon.** At least one seasonal/operating year plus subsequent expansion/renewal decision.

**Retention/correction.** Preserve site, vehicle generation, shift definition, tonnage cumulative window and methodology changes. Cumulative tons cannot substitute for a contemporaneous utilization denominator.

**Strongest alternative.** The deployment is operationally successful but economically specific to a labor-constrained flagship partnership or subsidized/strategic terms that do not generalize to fully priced commercial sites.

**Falsifier of the commercial-payback thesis.** Matched full cost per accepted ton fails to improve or a later site declines to expand/renew despite comparable labor and operating conditions.

**Existing intended owners.** GMI for deployment assertion; Industrials/financial owners for equipment/segment economics; existing identity/evidence owners; lane A only where agricultural customer economics are later reused.

**Currently unmeasurable.** Bull Run project price, supplier margin, support/supervision hours, autonomy-specific capex and matched cost per ton.

## 6. Observation profile C-O4 — machine-vision task economics

**Qualification: SUPPLEMENTAL PRELIMINARY.** Exact acquisition feasibility, information/review cadence, retention horizon and complete source binding remain unqualified. This is a research prompt, not an enrolled observation contract.

**User question.** Does a qualified vision installation improve a specific inspection/guidance task enough to justify installed hardware/software and integration cost?

**Population.** Same production cell/line, task, product mix, camera/sensor/lighting/software version and measurement window.

**Exact observables.**
- inspected/guided units;
- accepted defects, false rejects and escapes where relevant;
- throughput/cycle time;
- downtime and intervention;
- hardware attachment and replacement;
- software/license/support;
- integration/calibration/training;
- seller price/revenue scope;
- customer scrap/rework/labor change.

**Denominators.** Per inspected unit and per available line-hour; defect metrics retain eligible-unit denominator. Do not use a demo accuracy score as production yield.

**Current evidence.** ROBOT1 provides Cognex/Orbbec/Mujin technical roles and specific inclusions, but no source-qualified factory ROI case in this child.

**Alternative/falsifier.** Technical capability may already be bundled in the cell or may shift defects/rework without reducing full cost. Falsifier is no sustained quality/throughput benefit after integration/support cost.

**Existing owners / missing.** Semiconductor/Robotics owners retain device facts. C needs a customer task + seller economic bridge. Exact candidate application and source feasibility remain UNSELECTED.

## 7. Observation profile C-O5 — medical robotics comparable operating cohort

**Qualification: SUPPLEMENTAL PRELIMINARY.** Complete acquisition, information/review cadence and retention details remain unqualified. Reuse of Healthcare/B does not by itself supply an observed comparable operating cohort or enroll a native contract.

**User question.** Does a placed medical robotic system become sustainably utilized under its commercial arrangement without conflating clinical access with physical placement?

**Population.** Same system/version, geography/site type, placement/lease arrangement and procedure family.

**Exact observables.**
- placements and arrangement (capital/operating/usage-based, preserving nested categories);
- average active system-days;
- procedures by compatible scope;
- service/training/upgrade burden;
- recurring instruments/accessories only where procedure scope reconciles;
- contract revenue/cash timing.

**Current evidence.** Healthcare R4 already distinguishes placements, installed base, procedures, nested leases and recurring economics. Lane B owns patient, clinical, payer and care-access interpretation.

**Alternative/falsifier.** Placement growth may shift supplier financing/cash timing without creating proportional utilization. A ratio built from instruments revenue and an unreconciled subset of procedures is invalid.

**Owner seam.** C does not duplicate clinical review. It consumes B/Healthcare's supported access/use evidence and adds only complementary physical/commercial deployment observations.

## 8. Proposed dossier journey — research/design only

A useful future existing-owner dossier should answer, in order:

1. **What is the exact deployed object?** platform/system/version/site and ownership.
2. **What job is it supposed to perform?** workload/population and operating conditions.
3. **Is it merely announced/installed, or actually productive?** accepted output, utilization, availability and intervention.
4. **Who pays and how?** capex, lease, per-use, subscription, service, energy/transaction, public funding.
5. **Who carries the support/capital burden?** integration, training, maintenance, spares, remote assistance, replacement, financing.
6. **What economics are retained?** customer avoided/added cash and supplier/operator contribution/cash, with accounting profit, cash investment and financing kept as distinct scopes.
7. **What remains unknown?** visible gap with next discriminating observation and strongest alternative explanation.

No new universal score is proposed. A user should be able to see “installed but utilization unavailable” or “productive work proven but payback private” without a false completeness color.

## 9. Concrete investor workflows

**Workflow A — distinguish deployment from adoption.** Start from a theme leaf such as roboticslogistics, open a named deployment, inspect system/site scope, productive-unit evidence and support obligations, then see which economic link is still missing.

**Workflow B — challenge an installed-base narrative.** For EV charging, inspect reported energy and compatible realized revenue separately from a prospective capacity/availability model. Compare utilization only with integrated eligible exposure and a declared rate basis. The workflow should allow “more stalls, lower reported per-stall throughput” without forcing a verdict about mature sites or attributing energy growth to expansion from aggregate closeness. Then inspect separate accounting-profit and cash-investment/financing views.

**Workflow C — compare different monetization models without mixing them.** Contrast Symbotic deployment + support, EVgo usage/energy + network revenue, and Caterpillar equipment/autonomy/dealer support using their native units rather than forcing a universal revenue multiple.

**Workflow D — reuse adjacent owners.** Medical robotics opens Healthcare/B evidence for care/payer questions; agricultural autonomy opens A evidence for grower economics; chip content opens Semiconductor evidence; connectivity opens Communications. Reuse source identity and interpretation seam without counting another lane's conclusion as independent source confirmation.

## 10. Machine behaviors and discriminating future acceptance examples

A future accepted implementation should, at minimum, demonstrate:

- a contract target and an achieved uptime observation render as different facts;
- 77 systems in deployment and 56 operational systems are not summed into 133 installations;
- usage-based leases remain nested within operating leases;
- fixed observed kWh and compatible realized yield produce unchanged measured charging revenue when unrelated stall/availability metadata changes;
- a kWh/available-hour rate receives the compatible availability factor once; a kWh/all-scheduled-hours rate receives no additional availability factor;
- 99 GWh retains its PUBLIC-network source population; the 3,930 end-quarter count cannot establish quarter stall-days or validate reconciliation merely because 3930 × 276 × 91 is close;
- staggered commissioning distinguishes 137 integrated stall-days from 182 endpoint-derived stall-days in the declared synthetic fixture;
- regulatory credits/OEM-network revenue are not silently treated as charging tariff;
- identical hypothetical cash flows reconcile through accounting profit plus included D&A addback minus cash capex once; interest and capital offsets cannot be counted twice;
- cumulative autonomous tons do not become tons/hour without operating-hour denominator;
- a source correction preserves predecessor and historical applicability, invalidating dependent calculations AND prose but not unrelated observed totals;
- one source/event reused across multiple leaves remains one source lineage;
- missing site capex, working capital, taxes or intervention labor yields a bounded limitation, not zero;
- private/current full-fidelity research is never emitted through an unapproved public path;
- the research view changes no basket membership, rank, entry, size or trade output.

These remain proposed product acceptance examples for the Meta-CEO/Fable integration package, NOT_EXECUTED as product tests. The separate offline `test_measurement_repair.py` runs synthetic arithmetic/counterexamples for C-R1–C-R3 only; those results do not execute or validate any native interface or issuer disclosure.

## 11. Integration constraints

Use current source owners; do not create:
- a second evidence graph;
- an automation-deployment registry;
- another identity master;
- a new financial store;
- an ingestion daemon or watcher;
- a deployment score;
- a parallel publisher.

GMI contributes source-local research and evidence-qualified interpretation. Existing identity, financial/Earnings, source-rights, Research Vault/private publication, K1/relationship, F04/shared detail, forecast/evaluation and market owners keep their authority.

C-R1–C-R4 correction authority: parent #7886/comment5810356948 and detailed review section 4 at `30cca9d7a216f94580104444c405fc31064c7e48`. Original research and source evidence are retained; no new broad study, private-ROI acquisition or implementation is performed.

MISSION_COMPLETE: false
