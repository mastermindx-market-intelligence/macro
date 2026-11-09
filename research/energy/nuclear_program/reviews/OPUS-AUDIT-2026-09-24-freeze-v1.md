# Opus READ_ONLY audit of freeze v1 (checkpoint 98b75bbf §3–§5) — 2026-09-24 ~05:16Z

Commission: seat 8955bbc3, ROUTE review / AUDIT, MODE READ_ONLY, model opus. Verdict: **FIX_REQUIRED** (9 BLOCKING, 3 ADVISORY). Seat adjudication: **all 12 accepted**; freeze v2 written in the checkpoint §4–§5 at the next carrier commit. Uncovered-ENE list consumed: ENE-05/08/11/12/13/17/19/23/24/25/30/31/33/34–38/41/47/49/65/66 each now have a typed field or law in v2 (see §4 "ENE coverage additions").

| # | Class | Finding (field / rule) | Failing input | Seat action in v2 |
|---|---|---|---|---|
| B1 | BLOCKING | §7 section set claimed but `comparisons`, `native_context`, `provenance.mode`, `authority.can_veto` absent | Cameco O01 price-minus-cost; Technology §8 midpoint decomposition | added all four |
| B2 | BLOCKING | Energy bounds hard-coded in the shared schema; no pagination reserve | Technology 25/50/100 with pagination | schema ceilings 50/200/400/100/100; composer bounds in `coverage.bounds`; `continuation` reserved null |
| B3 | BLOCKING | oversize handling contradictory (refuse vs raise vs minItems 1) | 6-subject selection | subjects minItems 0 + if/then with `OVERSIZE_SELECTION`; "refuses" = typed dossier, never raises |
| B4 | BLOCKING | `milestone_flags` nuclear-specific and inconsistent with §3 names; law untestable | NuScale E06 / Oklo E05 fixtures | `milestone_assertions[{vocabulary, flag, value}]`, core + energy vocabularies, `evidenced_by` law |
| B5 | BLOCKING | nested backlog / equity-method laws have no field | Cameco O04, Centrus O05 | basis `equity_method_investee_full`; `contained_in`; `additive_with_siblings`; `DEFINITION_INCOMPATIBLE` law |
| B6 | BLOCKING | bridge steps lack status/basis gates | Centrus E02 forward → observed operating_contribution | closed bridge compatibility table, one test per row |
| B7 | BLOCKING | restricted rights still carry values; roles/narratives have no rights state | `rights_state=restricted` + `value.point` | if/then value null; `rights_state` on role, bridge step, counterevidence |
| B8 | BLOCKING | `knowledge_cutoff` never compared to clocks | cutoff 2026-08-01 with BWXT Q2 published 08-03 | `AFTER_KNOWLEDGE_CUTOFF`, `KNOWLEDGE_TIME_UNKNOWN`; AVAILABLE expectation needs `first_known_at` ≤ cutoff |
| B9 | BLOCKING | closed enums contradict "pluggable"; `correction` kind and scalar `basket_relation` collapse distinctions | GEV in three baskets; STSI conflict classes | `conflict_class` + `domain_code`; `revision_kind`; `basket_memberships[]` |
| A10 | ADVISORY | counterevidence law per subject, not per favourable claim | Centrus role-only counterevidence | per observed/forward step and per hypothesis relationship; else downgrade + `COUNTEREVIDENCE_MISSING` |
| A11 | ADVISORY | "refused" undefined; unreachable laws; ROLE_KINDS unlisted; dossier-level authorship; wrong section refs | — | law→action table; `authority_bits` input; `security_link_allowed` on subject; enumerated ROLE_KINDS; per-narrative `authored_by`; refs fixed |
| A12 | ADVISORY | ordering keys, fingerprint algorithm, decimal pattern, nullable counts, FormatChecker, change-level R5 grade misuse | — | explicit sort keys; sha256 canonical JSON; decimal regex; nullable ints/preliminary; `Draft202012Validator(format_checker=FormatChecker())`; `source_class` replaces change-level grade |

`role_kind` answer: string + vocabulary kept, but the schema now pins the vocabulary id grammar, lists registered vocabularies with if/then validation, constrains `other`, and adds `role_facets[]`.

GAPS the auditor named (unchanged): #7870's `semiconductor_theme_research.v1` shape, #7788/#7773 designs and the R5 grade definitions were not read; the Power-Demand supplemental relation of `power_grid` was not verified.
