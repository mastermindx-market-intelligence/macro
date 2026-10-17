# Prophet H1 prospective accrual contract — R1

Status: parent-adopted prospective source contract for the original Prophet track. This is **not** experiment admission, model execution, product authority or a substitute for the accepted H1 scientific specification.

Protected procedure at publication: Mastermind `c7407c6c77ef82cc6590401e80cc8f1868dc9085`, Skillpack 1.0.1 / bootstrap 1.

Scientific baseline: `research/prophet_recovery/scientific_successor_1/SPECIFICATION_R1.md` and parent acceptance `DEC-PROPHET-H1-SCIENTIFIC-BASELINE-ACCEPTANCE.md`.

Current source disposition: **PROSPECTIVE_ONLY / HISTORICAL_SOURCE_UNAVAILABLE**. The currently accessible compute hosts and configured repository data roots contain no real `data/us_prophet_rank/candidates` or `data/us_prophet_rank/grades` parts, and no lawful historical US grade catalogue/rights receipt was recovered. No outcome values were opened to reach that ruling.

## 1. Start event

Prospective H1 does not start when code exists or a PR turns green.

The **candidate-capture start session S0** is the first ordinary exchange session after accepted #8091 source release for which the normal production/nightly path writes a non-empty native Context Vector candidate part and its source receipt can be read back.

The first ordinary nightly proof must record:
- exact released source commit;
- exact expected US exchange session;
- native candidate part path and content receipt;
- row count and original four-key population identifiers available for that session;
- board_definition/source-generation identity;
- candidate/context feature availability and typed missingness;
- no change to live ranking/entry/size/plan authority caused by capture.

A green source CI run is not S0. A manual or synthetic fixture is not S0. A missing/empty candidate part means S0 has not occurred.

## 2. Prospective source fields that must accrue

### Candidate/context store

Per `engine.us_context_vector`, the nightly part must retain the original PIT target row and, where supplied by native owners, at least:

- `stamp_date`, `ticker`, `board_definition`, `lane`;
- `security_id`, `issuer_id`, `identity_epoch`, `identity_epoch_state`;
- identity capture basis and exact identity-source digests;
- `cycle_state` + `cycle_label` as one atomic owner pair;
- cycle vocabulary digest;
- PIT membership IDs and exact membership source digest/version/curated date;
- `theme_capture_group_id`, group-state/rule/weighting;
- exact member roster/member-set witness where the accepted capture supplies it;
- market/regime/context dimensions already emitted by the native Context Vector;
- source-availability states rather than synthetic backfills.

The original Context Vector keep-first key remains `(stamp_date, ticker, board_definition)`. A rerun cannot silently rewrite a previously stamped night.

### Grade metadata store

After labels naturally mature, the native grade writer remains the sole forward advancer.

The accepted strict metadata reader may project only its existing non-return metadata vocabulary, including:

- native grade key `(stamp_date, ticker, board_definition, horizon)`;
- `fill_date`, `mark_date`, `bench`, `graded_asof`, `schema`;
- native discriminator/signal class/signal label;
- benchmark calendar state, inserted-session count and missing-session witness.

A lawful strict read additionally requires the already-authorized catalogue:
`relative_part -> {sha256, bytes, rows}`.

The strict reader does **not** establish:
- source rights;
- candidate-population completeness;
- label usable time;
- economic identity validity;
- selected-price basis;
- experiment admission.

Those remain separate gates.

## 3. Price/source evidence

For every candidate/date used by H1, the eventual source manifest must bind the selected-price evidence through the accepted Data OS source path once #8183 is released.

Required fields are:
- actual selected source/rung;
- relative source object;
- actual selected price column;
- supported adjustment basis `raw | sadj | tradj`;
- exact encoded-object digest/byte receipt used for decoding;
- explicit typed unknowns for any unattested adjustment vintage, session, venue or observation clock.

File access never proves rights. A later path reread cannot authenticate previously consumed numbers.

## 4. Expected-session calendar and missing nights

Before any protected result access, instantiate a literal US exchange-session calendar from S0 forward.

Every expected session is retained in the manifest, including:
- normal capture;
- zero-candidate capture;
- candidate-store failure;
- nightly failure/cancellation;
- delayed/missing grade maturity;
- exchange halt/closure where applicable.

A failed or missing session never disappears from denominators merely because no candidate/grade part exists.

## 5. Fixed prospective allocation

Per accepted H1 R1, if no admissible untouched history exists:

- first **126 expected sessions** from S0 = training block;
- next **42 expected sessions** = calibration block;
- next **252 expected sessions** = final test block.

Total planned calendar allocation = **420 expected sessions** before post-test label maturation.

These are fixed planning windows, not a power guarantee. Do not shorten them after seeing results. Any different allocation is a versioned, pre-outcome parent amendment.

Support purging remains exactly as specified:
- retain actual primitive feature support;
- retain actual label support `[fill, mark]`;
- retain actual label-known/usable time;
- purge earlier rows whose label support or usable time crosses the next block's protected boundary;
- never move a purged row into another block.

## 6. H10 timing law

For each original stamp session `t`:

- native fill = close at the bar strictly after the original stamp bar;
- H10 mark = close at fill index + 10.

Under a contiguous native session series, the nominal mark is therefore roughly **11 exchange sessions after the stamp**. The actual source/session support controls; missing bars, halts or unclear terminal evidence remain unresolved and are never silently resnapped.

**Earliest first formal H1 look:**

`first scheduled native publication at or after [label-support end of the final planned test session] + 5 expected source sessions`.

Do not replace this with a guessed calendar date.

A convenient lower-bound planning expression, valid only if every expected session is captured normally, is:

`S0 + 420 planned sessions + final H10 label support (~11 sessions) + 5 source sessions`.

This expression is not a guaranteed date. Actual calendar instantiation, source gaps, purges and label support may push the first look later.

## 7. Coverage and completeness gates

Before the single formal look:

- base-input coverage >= **70%** of source-native target issuer/dates;
- q=1 peer-history coverage >= **70%** within the base field;
- both coverage checks also pass by registered monthly slice;
- >= **70%** of expected final-test sessions support the original K5 comparison;
- training-label coverage >= **95%** of otherwise base-eligible training rows;
- **100%** of originally selected paired dates must have all required selected stock and benchmark marks for positive qualification of the full frozen estimand.

Undefined denominator = `UNESTIMABLE`, never 0% or 100%.

Missing/delisted/failed sources remain represented. Do not impute cash, assume a delisting loss, winsorize unknown outcomes or assume missing-at-random.

## 8. Pre-outcome readiness/refusal states

The accrual layer must be able to return one of:

- `CAPTURE_NOT_STARTED`
- `CANDIDATE_CAPTURE_DARK`
- `IDENTITY_UNRESOLVED`
- `GROUP_SOURCE_UNAVAILABLE`
- `GROUP_AMBIGUOUS_OVERLAP`
- `UNSUPPORTED_WEIGHTING`
- `MEMBERSHIP_ROSTER_INCOHERENT`
- `PRICE_EVIDENCE_UNAVAILABLE`
- `PRICE_BASIS_UNATTESTED`
- `RIGHTS_UNVERIFIED`
- `GRADE_STORE_NOT_MATURE`
- `GRADE_CATALOGUE_UNAVAILABLE`
- `LABEL_USABLE_TIME_UNVERIFIED`
- `INSUFFICIENT_COVERAGE`
- `INSUFFICIENT_SUPPORT_SPAN`
- `PROSPECTIVE_ACCRUAL_IN_PROGRESS`
- `EXECUTION_BOUND_REVIEW_REQUIRED`
- `SOURCE_READY_FOR_REGISTERED_BATCH`

These are research/source states only and have no live rank, entry, plan, sizing or trade authority.

## 9. Pre-outcome known-answer smoke

Before any protected result access, one deterministic smoke must prove:

1. candidate row and grade metadata join only on the native grade key;
2. unresolved original target keys remain in denominators;
3. duplicate/conflicting original keys fail closed;
4. q=0 routes C1 and C2 to the same C0 fallback;
5. q=1 requires the accepted sole-active-group rule and complete compatible peer windows;
6. focal issuer is excluded from peer history;
7. feature support and label support clocks are distinct;
8. metadata-only grade reads never materialize outcome columns;
9. missing selected-price/rights/identity evidence yields a typed refusal;
10. no smoke output contains H1 returns, ranks, fitted coefficients or outcome-sorted lists.

Passing this smoke still does not authorize the protected batch.

## 10. One-look and claim boundary

H1 retains exactly one formal registered experiment:
- C0/C1/C2 fixed arms;
- C2-C1 primary;
- K=5;
- H10;
- fixed gain/downside/precision gates;
- fixed coverage/concentration/attribution diagnostics;
- no hyperparameter, feature, seed, horizon, benchmark or split search.

At the first formal look, unresolved selected outcomes remain unresolved; do not postpone the look until convenient outcomes appear.

Even a successful H1 result would support only a bounded shadow-qualification decision for the admitted US curated-momentum population. It would not establish:
- causal acceleration;
- probability of winning;
- four-market portability;
- entry timing;
- holding duration;
- position sizing;
- executed profit.

## 11. Release dependencies

Prospective accrual cannot be declared live until:

1. #8091 accepted source release;
2. first ordinary nightly candidate/context readback;
3. subsequent normal nightly continuity;
4. native grade writer creates mature grade parts after H10 support exists;
5. authorized grade catalogue/rights receipt exists;
6. selected-price evidence source is accepted and available through the existing consumer;
7. execution-bound preregistration review binds exact code/environment/trial/budget.

#8183 selected-price evidence may improve source truth independently, but it does not start H1 or create a historical source.

## 12. Current programme status at publication

- H1 historical source: unavailable under currently accessible evidence.
- H1 source mode: prospective-only.
- #8091: source candidate exists; first natural prospective nightly not yet accepted.
- #8183: selected-price evidence candidate exists; release remains separately gated.
- No protected H1 outcomes have been opened by this contract.
- No H1 model has been fit.
- No live Prophet trading authority changes.

MISSION_COMPLETE:false.
