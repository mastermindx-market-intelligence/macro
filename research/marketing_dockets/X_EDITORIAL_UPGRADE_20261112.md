# X editorial quality and publishing upgrade

Operation: `marketing-x-editorial-upgrade-20261112-c2`.
Repository: `mastermindx-market-intelligence/macro`.
Initial source: `54465f90b32b39f704ece828638eccb5f079c397`.
Protected procedure: `Mastermind@c0b30b422d2310e614f91faed49a4adbce4291f0`, skillpack 1.0.1 / bootstrap 1.
Owner: current Chairman-assigned ChatGPT2 session; source authoring through this isolated GitHub branch. This document is a delivery companion to the existing marketing suite/content-studio plans, not another runtime or workstream registry.

## Outcome and completion standard

Upgrade the existing X marketing system so its output is useful, coherent, evidence-grounded and naturally written; its visuals are readable in a phone feed; its admin suite makes editorial decisions and delivery evidence clear. Preserve the existing source, outbox, provider, approval, cadence and publication owners.

Completion requires the actual generation/review/media/admin consumer paths, affected automated checks, normal source release, and production/browser proof. A plan, passing fixture or merged PR alone does not complete the assignment. Engagement improvement is not claimed without prospective measurements.

## Source findings and existing boundaries

- `engine/marketing/earnings_call_lane.py` appends a generic research/trading disclaimer to every candidate, including an empty-content fallback. Other voice gates already reject disclaimer endings.
- `copy_critic.py` is the existing cold-reader owner; `copy_auditor.py` owns batch review. Extend these instead of adding a competing grading service.
- `admin/static/styles.css` constrains chart previews to 200px high. The phone preview must preserve legibility and offer a full-size view.
- `admin/marketing_floor.py` and `flrLine` mix counts from different populations into a conversion funnel. Missing cohort lineage must suppress yields/loss conclusions.
- Provider booking is not confirmed public delivery. Reuse existing receipt and metric evidence; do not rewrite publication history.
- PR #7493 owns the editorial compiler in `copywriter.py`, `config/marketing.yml`, and its v2 tests. PR #8302 owns its frontier/shadow consumer. PR #7489 owns outbox/media recovery and publisher mutations. Their holds, reviews, unsettled effects and original carriers remain untouched. This phase uses separate paths and does not reproduce their held effects.
- Catalyst activation and its held flags remain with the existing WS:MARKETING-X-CATALYST-LOOP; source expansion does not enable them.

## Delivery tree

| Node | Outcome | Input / scope | Acceptance |
| --- | --- | --- | --- |
| P1 | Useful earnings-call copy | Existing committed call-event schema and earnings-call projection | No automatic disclaimer, no empty-content fallback, coherent supported qualitative content; numeric/advice/provenance/freshness/dedupe guards preserved |
| P2 | Better editorial judgment | Existing critic/auditor and intelligence writer contracts | Explain reader value, distinguish inference from facts, actionable repair reasons, no fabricated personal experience or unsupported causes; current public APIs and provider routes retained |
| P3 | Readable visual review | Existing marketing chart/render and admin media path | Large readable preview, mobile-feed preview, exact aspect ratio and safe media handling; deterministic evidence charts retain exact data |
| P4 | Trustworthy publishing suite | Existing admin projection/API/frontend | No incomparable conversion percentage, booked vs confirmed distinguished, actionable current issues separated from history, source review visible, stale retry controls match existing backend guards |
| P5 | Broader high-value content | Existing qualified dashboard source adapters | Reuse evidence-rich source families, explicit support for interpretation and visual purpose; no new data rights, provider, scheduler, duplicate source store or publication activation |
| P6 | Qualification and release | Integrated owned diff | Focused tests, dark/light and desktop/mobile UI evidence, exact-head CI and permitted incumbent release; then live proof |

P1 and P2 can proceed independently of the held editorial/compiler carriers. P3 and P4 share one root writer and are composed before UI proof. P5 follows the source-contract audit. P6 consumes each stable coherent result without declaring the parent complete early.

## Product decisions

- Facts remain traceable. Opinion means a conclusion supported by those facts, with a meaningful condition when needed. It never supplies a new price, catalyst, causal claim, target or probability.
- Remove boilerplate at its generating source; do not blindly strip quoted or deliberately required disclosures.
- Do not force every wire update into a contrarian opinion. Analytical content should answer a reader question.
- Reuse chart libraries and image machinery. Accurate charts/labels are deterministic; illustration generation must not invent quantitative evidence.
- Dark: calm graphite surfaces, restrained semantic ink. Light: cool canvas, white surfaces, clear hairlines. Both use incumbent admin/theme tokens and identical workflow semantics.
- Exact copy and media take priority; technical receipts and historical terminal records live in expandable detail. No decorative colored card edges.
- No new direct X sends, blanket approvals, account activation, spending or provider settings are part of source qualification.

## Execution and proof

Fabric capability read reports `adapter_available=false`; no worker request was submitted and no modifying worker started. Direct implementation reason: `NO_ELIGIBLE_PRE_EFFECT_WORKER` with lawful isolated GitHub source access. Native children are read-only editorial/systems architecture critics, not substitute implementation workers. WHY NOT FABLE: no additional principal or account is needed; the current assigned session integrates bounded judgment and source changes.

Initial milestone: source/collision census complete. No source code or live configuration changed yet.
Next: implement P1 and the existing-review improvements, then compose the admin consumer fixes and verify them.
