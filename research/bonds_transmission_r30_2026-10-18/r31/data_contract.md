# R31 data and owner binding contract

This is a UI integration requirement, not a new registered data schema or parallel service. R30 source semantics remain in force. The exact source owners identified below resolve the earlier “owner unknown” task while leaving their required bond-specific extensions explicit.

## Source pins

| Repository | Inspected commit | Purpose |
| --- | --- | --- |
| Mastermind | 0d51da5463a18a251905ec0ef5a580ccdb0b3546 | Current protected procedure and target-scoped Paper workflow |
| Macro | 4f52d22596545cbd67b5143e188baf5660237024 | Existing programme, design doctrine and owner discovery |
| mastermind-terminal | d6515f47232538161af8d3d4c27064165eda40fe | Investigation, Alerts and watchlist implementation |

The source reads establish code and contract presence at a pin. They do not establish current production deployment, end-to-end acceptance, live source entitlement or empirical model quality.

## Existing research owner

Terminal Investigation v2 owns research identity, immutable revisions and retry receipts.

Inspected paths:
- docs/INVESTIGATION_V2_CONTRACT.md
- terminal/lib/investigations.ts
- terminal/lib/investigationContracts.ts
- terminal/app/api/investigations/route.ts

Source-discovered reuse paths include terminal/lib/investigationSave.ts, terminal/lib/analysisRoute.ts and terminal/components/RetainedInvestigationLayout.tsx. These additional paths were located by source search; a complete implementation review of those files was not performed in this design pass.

Existing endpoint family:
- GET /api/investigations
- GET /api/investigations?id=<uuid>&revision=<n>
- GET /api/investigations?operation_id=<uuid>
- POST /api/investigations with the existing InvestigationCommand.

The command includes identity, operation_id, expected_revision, action and manifest, with optional layout capture. Current actions include create, revise, remove and restore. Identity and authorization remain server/session-derived; client-provided ownership is not authority.

The manifest is investigation_manifest.v2. Its established areas are intent, layout_refs, thesis_refs, evidence_refs, continuation and an optional review baseline. The current service admission is narrower than the general type grammar:
- terminal.analysis_symbol: security subjects.
- data_os.security_master: security or issuer subjects.
- earnings.workspace_generation: event_workspace evidence.
- Current G1 admits no thesis references.
- Bond/CDS/flow evidence and scenario/relationship/note payloads are not automatically admitted.

Known contract bounds include a 160-scalar title, 4,000-scalar question, 4,000-scalar continuation, 16 subjects, 4 layout references, 128 total references and 128 KiB serialized payload. These limits do not provide a way to hide unsupported scenario payloads in text.

Required implementation extends the established reference/admission/resolver path for typed bond evidence and retained scenario assumptions. Do not create a second case database or treat terminal watchlists as the investigation owner.

Storage/read contracts already distinguish the mutable head, immutable investigation_revisions, investigation_mutation_receipts and retained chart-layout revisions. Exact operation replay resolves its receipt before head checks. The same operation with a different payload conflicts. Expected revision supplies compare-and-swap semantics.

Preserve error meaning: unauthenticated, inaccessible/missing, revision conflict, invalid transition/reference, limit and unavailable are separate UI states. Missing and foreign resources share the established inaccessible response; avoid ownership disclosure through error copy. Read-only review performs no save, scheduling or agent activation.

## Existing monitor owner

Terminal Alerts remains the monitor owner. The inspected route is terminal/app/api/alerts/route.ts. Its allowlist includes legacy signal/regime/price/rsi, specific options conditions and suite_event/suite_sequence. It rejects unsupported condition types.

The R30 yield threshold + matched credit-basket change + funding state rule is not admitted by that generic allowlist. Required implementation belongs in the existing condition schema, evaluator, dry-run and receipt path. Do not introduce a separate monitor store or use a “price” condition to carry an unrecognized compound expression.

Source search located the existing /api/alerts/dry-run, /api/alerts/receipts, terminal/lib/alertDryRun.ts and terminal/lib/alertsView.ts paths. Their existence is reuse evidence; this pass did not execute those APIs.

Until the full conjunction, clocks, expiry and invalidation precedence are supported, the design must show monitoring unavailable. Separate alerts are not a semantically equivalent implementation of an AND rule. The existing R30 five-eligible-close lifecycle and explicit funding invalidation remain the target behavior.

## Analytical evidence requirements

These fields describe integration requirements for existing owners, not a new production API.

| Area | Required identity and evidence |
| --- | --- |
| Market structure | Instrument/series identifier, yield or return basis, adjustment method, market timezone/calendar, observation and availability clocks, horizon, source receipt, vintage and stale status |
| Volatility distance | Exact twenty prior daily changes, method/version, sample count, units, excluded-current-observation rule and null reason |
| Key-rate sensitivity | Position, curve family, maturity node, bump/interpolation method, valuation cutoff, sensitivity unit, vector coverage and calculation mode |
| Reported obligations | Filing/accession, reporting date, issuer, legal obligor, currency, principal/interest/lease/commitment type, amount semantics, date precision, event trigger and amendment |
| Cash pools | Owner entity, currency, cash balance basis, restriction, permitted use, transfer route and availability clock |
| Facility availability | Commitment gross/net semantics, drawn balance, letters of credit, borrowing-base cap, borrower/purpose/covenant eligibility, draw window, net proceeds, fees, interest and settlement cutoff |
| Buyer flows | Holder and asset scope, reporting period, market-value holdings, sourced transactions, price revaluation, FX, other changes, reconciliation residual and estimation status |
| Funding pipes | Repo measure and comparator, collateral/counterparty convention, market depth, dealer/holder coverage, release frequency and source cutoff |
| Retained case | Existing Investigation identity and immutable revision, admitted typed references, frozen assumptions, exact observation receipts and explicit draft/current/saved modes |

Do not confuse observation time, source publication, ingestion, build and user review time. Quarterly holder series cannot be silently cast as daily measurements. A current graph may show a slow series, but its period and publication clock remain visible.

## Arithmetic and missingness

- Use unrounded values for comparisons; round only presentation.
- Zero means observed or explicitly assumed zero. Unknown is null with a reason.
- Complete key-rate coverage is required for shape mode. First-order and convexity-inclusive results retain distinct method labels.
- Initialize opening cash once. A later financing balance does not erase a payment-cutoff deficit.
- Cash coverage needs legal usability and schedule completeness; annual reporting buckets cannot produce an exact daily gap.
- A market-value reconciliation residual is not automatically an observed transaction.
- Keep user assumptions, reported facts, model estimates and synthetic fixtures distinguishable through every transition.

## Continuation intelligence and empirical qualification

I13 technical structure and I02/I05 sensitivities supply descriptive and conditional evidence. I14 tests a proposed mechanism. None supplies a calibrated likelihood on its own.

The existing I09–I12 replay/model pathway remains the route to empirical qualification: freeze the information cutoff; define the target, horizon and competing mechanism; preserve contrary cases; avoid feature/outcome leakage; account for overlapping episodes and revisions; evaluate held-out calibration and abstention by regime and coverage. Qualification requires an admitted owner/model version and reproducible evidence. A count of correlated indicators must never manufacture a probability.

No live CDS source, measured buyer-switch feed, current borrower-specific cash schedule or qualified forecast was established merely by designing these views.
