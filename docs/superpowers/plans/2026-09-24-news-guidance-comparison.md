# Owner-bound guidance comparison implementation plan

**Goal:** Compare accepted Company Intelligence guidance records and carry the result through the existing News per-ticker projection, without inference, a new source store, or trading authority.
**Architecture:** A pure consumer validates existing workspace identity, measurement and source-span associations. The existing financial News projection receives explicitly supplied owner-native current/prior workspace pairs; the existing build_news writer forwards them. Automatic acquisition and HTML/UI rollout are not claimed by this leaf.
**Spec:** Macro #7953, Chairman-approved end-to-end proposal. Existing Company Intelligence event_workspace.v1/guidance_item.v1/documents.py remain the source owners.
**Tech stack:** Existing Python code; Decimal arithmetic; pytest; no new runtime dependency.

## Scope and authority
- Protected Skillpack: Mastermind@605cd056c3463c992d85ba76dbcc90fbb758da75, version1.0.1/bootstrap1. Current Chairman continuation retains source authority. Direct work reason: PRINCIPAL_JUDGMENT over the source/consumer boundary plus LOWER_TOTAL_OVERHEAD for the pure leaf.
- The current outer adaptive-mode Bootstrap governs this Web session over the older companion's fixed mode/duration assumptions; no runtime admission or model telemetry is inferred. The same source gates remain mandatory.
- Macro base: 3a29e6145ce53ca4551adef866a5f73e62c8c4ff. No writes to shared/denied Cluade/lanes paths. Use the permitted selected-source evidence snapshot, not a claimed acquired production workspace.
- Keep #7955/#7966 immutable; preserve #7591 mobile and #7575 extractor/formatter ownership. No third extractor, history service, news identity, public route, queue, or model activation.
- #7966's exact-head CI and Fences are now SUCCESS; independent review is still absent. #7955 has its recorded inherited CI failure and review gate.
- The existing public Company Intelligence R2 marker returned HTTP403 in the one bounded read. Do not retry/bypass that denial. Live source access and production acceptance remain held.

## Review focus
1. A different issuer or guidance period must never donate a comparison baseline.
2. Unknown financial measurement basis/currency cannot become comparable by matching raw amounts.
3. Corrected, withdrawn, duplicate, ambiguous or missing records cannot become a claimed company guidance raise/cut.
4. Nonfinite values, bools, reversed bounds and zero denominators must never manufacture a useful-looking percentage.
5. The consumer must preserve the existing News counts, sentiment and rank behavior when no owner pairs are supplied; no new ticker may be created from the auxiliary context.

## Files and interfaces
- Create engine/company_intelligence/guidance_comparison.py: compare_guidance_workspaces(current, prior, *, as_of) -> JSON-safe context-only projection. No I/O, network, ambient clock, LLM or source extraction. Inputs must come from the accepted owner; this consumer checks associations but does not certify the upstream extractor.
- Modify engine/financial_news.py: mastermind_by_ticker(feed_dict, *, guidance_workspaces=None, as_of=None). Auxiliary pairs keyed by existing ticker, with current/prior fields and the existing owner-supplied expected_security_id (venue-qualified). Current ListingAlias must cover as_of; prior may carry a former alias of the same issuer. Calls the one comparator only after listing membership is checked.
- Modify scripts/build_news.py: build(write=True, *, guidance_workspaces=None), forwarding pairs and its existing injected run clock. Default calls have no additional network or data reads.
- Create tests/test_news_guidance_comparison.py: real owner-created receipt fixtures, full negative matrix, and actual financial News consumer.
- Register this source-only suite in an existing appropriate source-gated CI step only after exact shared-subregion compatibility is established. Registration is an acceptance obligation, not optional future work.

## Execution
- [x] Write a failing comparison for same-period vehicle guidance100000-103000 ->76000-78000. Expected midpoint101500 ->77000, delta-24500, percent-24.137931. The fixture is synthetic, not proof of actual2024 possession or an accepted Li extractor.
- [x] Prove negatives for missing/ambiguous prior, mismatched issuer/horizon/unit/basis/currency, invalid clocks/numbers/spans, withdrawn guidance and unchanged revisions.
- [x] Add minimal implementation; preserve original workspace data and authority flags. Arithmetic describes a numeric difference, not a forecast or an assertion that management actually raised/cut guidance.
- [x] Add and exercise the real per-ticker consumer. Default output is unchanged; auxiliary context cannot alter score/lean or mint a ticker.
- [x] Verify source-only CI enrollment, mutation tests, and compatibility with the existing repairs. Preserve test-snapshot limitations.
- [ ] Publish once on the operation's own branch and draft PR after fresh material-source/collision checks. Hold for independent review, exact-head CI and live-source/UI acceptance; do not activate the denied source to make a demonstration green.

## Completion boundary
This leaf is not the full product slice. The automatic accepted-pair producer, actual News/ticker rendering, corrected-source fanout and real-path browser proof remain required before the parent can claim live comparison intelligence. The producer will use existing verified historical readers, not the known-now reader as decision-time history. No consensus is inferred.

## Executed result and evidence limits
- New guidance contract:63 tests. Initial40-test RED exposed the missing consumer; later state, precision, identity, malformed-field and CI enrollment additions were separately RED/GREEN verified.
- Current source plus existing Financial News/news_common/qkernel tests:180 PASS, exit0, Python3.12 in an isolated evidence-root venv.
- Three deliberately broken variants detected: omitted horizon/metric matching (2 failures), omitted listing-match guard (2 failures), wrong delta sign (1 failure). Candidate restored byte-for-byte, then180 PASS again.
- Combined with unchanged #7955 head29dc4ce4f5b3f03ba1fc5419a507b09e1b3b93d5 and #7966 heade963555df1d7a71ead116d641a85c07e17f84241:288 PASS. Their adjacent test and manifest deltas compose by actual clean three-way merge. Neither incumbent branch changed.
- Numerical serialization accepts at most64 significant digits,30 decimal places and absolute values up to1e30; unsupported input is explicitly absent, never rounded into a claimed observation. Within bounds midpoint/delta retain exact decimals; relative percentages are rounded6places; rates use percentage-point differences.
- Observation and source-availability clocks remain beside the calculation clock. Source corrections are labeled source_correction_difference, not management raises/cuts. Venue-qualified security_id is a required caller binding for News, not derived from a headline or domicile.
- The actual build_news.build writer is exercised against its existing by_ticker.json output; independent collection/ledger boundaries are mocked, not called. No keys/LLMs/network are used by the tests. Public context strips raw document/span/source-hash receipts; internal comparator keeps references to the existing source owner.
- Initial expanded-test environment misses (pandas/dateutil, then pyarrow) were resolved with test-only dependencies; no production change. A separate combined-proof run initially lacked unchanged news_llm.py; adding the pinned dependency resolved2 import failures. Those are test-snapshot setup gaps, not product defects.
- All pytest temp files now stay in unique paths under this operation's evidence root. An earlier default pytest cleanup hit an unrelated protected old temp tree; no cleanup or permission bypass was attempted.
- Targeted current PR search returned91 relevant candidates and no observed overlap on the four product/test paths. This is not a whole-open-PR census.35 shared-CI patches were inspected for this job; only #7366 affects the same earnings-release-identity owner, adding its separate launchd test/path declarations. Full three-way manifest composition with #7366 c347f6c7d736324f68572beeb3b4183861b2f015 is clean, preserving its step and the new comparison step. Source custody/merge eligibility still rechecked at release.
- Publication compatibility base:d3a4bee82462556c899645a59a5ea22b5f3af950. Every pinned source/test/fixture dependency in source-manifest.json remains byte-identical to the implementation base; protected Skillpack stays605cd056c3463c992d85ba76dbcc90fbb758da75. The operation's new branch was absent at preflight.

**Not claimed:** automatic accepted-pair discovery, historical decision-time proof, real source access, a live UI, full repository conftest/data-guard execution, independent review, merge or deployment. The existing R2 source read returned403; that lane is not retried. Default production News builds do not acquire comparison pairs yet. This is the tested calculation-to-existing-artifact consumer leaf, not the full user-facing upgrade.


## R6 same-carrier repair: arithmetic isolation and disclosure order

Self-adversarial review of #7982 head 1037d783fa34b965cd12a483ca091db6d37f1644
found 11 reproducible failures in 14 added cases. This is author hardening, NOT
independent review. No input collector, writer, UI, activation, dependency,
source identity, or execution authority was added or replaced.

- Pin a private Decimal context, including rounding, exponent limits and traps.
  Changing an unrelated caller's Decimal state no longer changes the same
  comparison or causes a decimal exception. Validate the supported magnitude
  ceiling with context-free copy_abs, never a rounded absolute value.
- Require nondecreasing source-availability time in addition to increasing
  observation time. A delayed older disclosure cannot become a new outlook
  simply because its bytes were received later. Equal source timestamps still
  allow separately observed source corrections; those remain labeled as such.
- Reject missing/blank document and span identities, and invalid document
  revisions. Two absent document identifiers do not establish a source binding.
  SourceSpan and the existing verified reader remain the evidence owners.
- Malformed accounting-basis collections produce the existing named absence
  rather than a TypeError that can discard the enclosing News projection.

Verification on the operation's existing isolated Python 3.12 snapshot:
- New comparison suite: 77 cases; original comparator 11 FAIL / 66 PASS.
- Repaired comparison plus existing Financial News/common/qkernel: 194 PASS.
- Restore the original comparator: the same 11 failures return; restore repair:
  194 PASS again.
- Existing composed #7955 + #7966 + repaired #7982 proof: 302 PASS. The first
  two PRs are unchanged; no whole-repository, network, browser or live claim.

Exact logs: r6-red.log, r6-green.log, r6-original-mutation.log, r6-restored.log,
r6-three-candidate-integration.log and r6-verification.json in the existing
operation evidence root. Every test uses its own operation-owned basetemp.

Release constraints remain: independent exact-head review, applicable concluded
CI and current-source compatibility. The predecessor's CI pack 10 reproduced
an unrelated markets-regime-strip render mismatch on its unchanged base; that
is not permission to bypass release. The live R2 source denial remains frozen.
Mastermind Executive read preflight now returns 401 / manual reauthentication
required; no request was submitted, and no alternate credential or dispatcher
was used. Authentication recovery is distinct from a Pro/Extra High switch.


## R7 — ticker News display (2026-09-26, same carrier)

Current Chairman explicitly directs operation without the incomplete Executive plugin.
No Executive authentication is required for this source-only continuation. Native Codex review
was attempted once in the existing ChatGPT realm; routing returned401, process exited1 and no
review was produced. No retry/provider switch, independent approval or worker START is claimed.

Bounded implementation: `lib/news_guidance_view.py` formats only the existing public comparator
output; `scripts/build_ticker_pages.py` consumes that view from its already-loaded News record;
`templates/ticker.html.j2` adds native details inside its EXISTING News section. No new source,
identity join, history, publisher, HTTP route, model or ranking. Default input absence adds no
panel and leaves existing headline/stance values unchanged. No #7591 mobile News mutation.

The presenter currently understands vehicle-delivery counts and revenue-growth percentages.
Unknown measurement semantics are visibly unavailable; it never invents a currency scale.
Values remain producer-supplied decimal strings, including relative percentages and percentage
points. Source-correction and missing-prior states stay explicit. Four comparisons are shown;
unsupported/omitted counts are disclosed. Original disclosure dates and calculation time remain
distinct. Public rendering does not leak raw source locators and preserves bilingual escaping.

Execution and proof:
- New tests first:30 RED; implementation30 GREEN. Three glance/singular-unit tests then RED and
  repaired. Guidance-only/no-headline case RED and repaired. Final display suite37 cases.
- Final display + existing comparator/Financial News/shared-primitives suites:231 PASS.
- Combined with unchanged#7955 and#7966 sources:339 PASS; shared CI three-way merge clean.
- Wider ticker suite in selected-source snapshot:19 FAIL/109 PASS/1 SKIP on UNCHANGED original
  builder/template, exactly the same19 failures as the changed candidate. Missing unrelated
  index/Pressure Watch/JS assets in this snapshot are not product fixes or waived CI.
- Existing earnings-release-identity code gate runs the new display suite; its minimal install
  line gains jinja2. No new CI job or runner.
- Real Chrome/Puppeteer fixture matrix32 cases, both themes/languages and390/1440 widths:
  keyboard Enter/Space, correct locale visibility and within-panel layout passed. Canonical
  viewport rerun uses390x844/1440x900 and preserves REST plus opened screenshots.
- Existing canonical capture emitter produced mastermind.p0_evidence.v2 through its PageDriver
  seam from recorded REAL browser bytes. Existing visual-evidence gate PASS. Design-system
  enforce-added PASS with0 new blockers. No invented parallel evidence schema or palette.

Evidence: `mockups/evidence/news-guidance-20260926/EVIDENCE.yml` and manifest/PNG siblings.
No live source pairing, independent review, deployment or product completion is asserted.
Keep DRAFT/HOLD-FOR-SOL, no automatic merge. Next accepted source input must still come from the
existing Company Intelligence owner; the previously denied source endpoint remains frozen.


## R8 — source-specific chronology and the actual dossier CI dependency

Continuation of the existing operation/PR/branch; no fourth carrier. Chairman's
instruction to proceed without Executive remains controlling. The native Codex
review routing401 and public source403 remain frozen; no retry or alternate
credential, provider or endpoint was used. Direct work: PRINCIPAL_JUDGMENT at the
source-clock/lineage contract, then LOWER_TOTAL_OVERHEAD for the bounded fix.
This is author-discovered repair, not independent approval.

### Reproduced failure and implemented boundary

- [x] Consume R7 contract-delta job108392754105 in run36237834477. It found one
  introduced dependency gap: conviction-profile is scope:exclusive and the
  ticker builder now imports lib/news_guidance_view.py outside its declared
  paths. Widen that existing job by exactly that path; no other job changes.
- [x] Reproduce the timing defect against the prior comparator: transcript
  guidance inherited the issuer-release lifecycle clock. Require the exact
  cited source's existing event_source_clock.v1 for transcript guidance;
  validate it through qa_exchange.validate_source_clock, including document
  and source-hash association. Unknown/missing clocks do not borrow release time.
- [x] Keep legacy lifecycle clocks only for a uniquely identified issuer-release
  source. Multiple release sources cannot share one assumed clock. Explicit
  unknown source clocks never fall back; unsupported source kinds are absent.
- [x] Apply observed/disclosed pair order to EACH guidance item's actual source,
  not an unrelated event-level release pair. Unchanged release clocks cannot
  hide a later supported transcript; a late-arriving older transcript cannot
  become a new outlook. All source times require zones and available <= recorded
  <= calculation time. Existing workspace validation remains in force.
- [x] Route the new absence reasons to the existing bilingual explanation:
  'Disclosure timing could not be verified.' No new layout/CSS or machine slugs.
- [x] Exercise actual financial_news -> existing by_ticker artifact loader ->
  actual ticker context/template for both source-time-known and unknown cases.
  Known transcript guidance prints15:10, not the sibling release15:00. Unknown
  guidance shows the explanation without numbers or private source locators.

### Proof

Comparison corpus97 cases; display corpus44 cases. Expanded current source:
258 PASS, exit0. Deliberately restore R7 comparator:22 FAIL/119 PASS across the
comparison/display corpus; restore current bytes:258 PASS. Deliberately restore
R7 manifest:the trigger regression fails. The ACTUAL run_ci_pack.load_legacy_jobs
and select_jobs also select no conviction-profile job for formatter-only input
under the old manifest, and select conviction-profile under the repaired one.
That is exact owner-selector evidence, not a full-repository contract census.

Composition with unchanged #7955 head29dc4ce4f5b3f03ba1fc5419a507b09e1b3b93d5
and #7966 heade963555df1d7a71ead116d641a85c07e17f84241:366 PASS, exit0. Their
source and remote branches remain unchanged. Shared manifest three-way merge is
clean. No network/vendor/LLM, source endpoint, or real data tree was used.

R7's four existing synthetic scenarios retain byte-identical public payloads
and actual-template HTML under R8:normal, correction, rate and missing-prior.
R7 screenshots remain their original captures, not newly claimed R8/live proof.
The new timing-absence and source-specific timestamp behavior is tested through
the actual template. No browser/theme/stylesheet modification is part of R8.

Test snapshot setup gaps were repaired with unchanged exact-head dependencies
before the valid source-clock RED. The first incomplete run's missing
public_wire import is not evidence of a product defect. The full repo and its
contract-delta census remain hosted gates, not claimed from selected-source tests.

### Input-lineage ruling — automatic acquisition is not yet safe to connect

The current Company Intelligence reader's read_all_event_source_revisions
intentionally deduplicates consecutive issuer-release source hashes. A synthetic
probe of its ACTUAL _receipt_from_revision/_dedupe_carry_forward_hops produced
one release-revision row for two workspaces with distinct guidance transcript
hashes but the same issuer release. Zero network calls. That behavior is correct
for the release-history consumer; it is not a complete guidance-history API.

Do not relabel that release projection, add a competing history store, or select
a supposed prior guidance from the newest two returned release rows. Existing
source owner #7331 already owns per-source clocks and revision-serving scope;
#7575's rejected guidance extractor/formatter remains separately owned. News
requires accepted guidance-document lineage, original source/observation clocks,
a real same-period baseline and existing security binding before automatic input
activation. R2 access remains separately unresolved. This ruling blocks only
unsafe automatic pairing; source and UI repair did not require Executive OS.

Exact evidence in the existing operation root:r8-trigger-red/green.log,
r8-clock-red-complete.log,r8-clock-green.log,r8-message-red/green.log,
r8-consumer-green.log,r8-original-clock-mutation.log,
r8-original-trigger-mutation.log,r8-restored.log,r8-combined.log,
r8-mutation-verification.json,r8-actual-ci-selector-proof.json,
r8-source-lineage-probe.json,r8-r7-render-parity.json.

Keep DRAFT/HOLD-FOR-SOL and no automatic merge. Current source changes require
fresh exact-head independent review and concluded CI; previous green runs are
not these bytes' acceptance. No automatic ingestion, production release or
end-to-end product acceptance is claimed.

Source-owner continuation reference consumed: #7331 comment5758713655 already
accepts the Li Auto integration boundary. It calls for the existing
`guidance_update` event type and a separate `extract_release_guidance` callback,
then the incumbent #7331/#7426 producer/publisher after #7575's reviewed repair.
Forecast updates, documentary corrections and actual outcomes remain distinct.
News does not reopen that design or acquire any incumbent source custody; the
new transcript-history finding is an additive consumer constraint, not a demand
to replace the release-only revision projection or re-approve accepted work.


## R9 — existing release history to News baseline selection (2026-09-26)

Approved parent mission continues on #7982; this is a bounded reader-output
consumer, not permission to fetch the denied source or take #7331/#7426 custody.
The earlier prohibition remains exact: an issuer-release index is not complete
transcript-guidance history. This slice consumes ONLY release-backed guidance
from the existing verified oldest-first single-event revision result.

`compare_release_guidance_history` selects the final release and its immediate
predecessor and delegates all calculations to the existing comparator. It does
not sort, search farther back for a convenient baseline, globally deduplicate,
read a network endpoint, or persist history. Every supplied revision must bind
the same canonical event and its own generation/source/lifecycle metadata and
carry the existing workspace receipt shape. Raw-byte authenticity and complete
chain acquisition stay with the existing reader; shape validation of a Python
dict is never represented as cryptographic verification.

The bounded consumer refuses more than 64 revisions instead of truncating;
requires increasing receipt order and nondecreasing disclosure order; rejects
duplicate generations/consecutive release copies while retaining A -> B -> A;
never revives an older outlook after a latest actual-only release. Transcript-
bound guidance is refused even when the same workspaces also contain valid
issuer releases. Missing prior, incompatible periods, source corrections,
physical counts/rates and exact existing security identity keep their existing
semantics. Scope is one existing canonical event, not invented cross-event
history or a new event/type alias.

Existing `financial_news.mastermind_by_ticker` now accepts owner output in its
existing optional input map as `{event_id, release_revisions,
expected_security_id}`. Explicit `{current, prior, expected_security_id}` inputs
remain unchanged. Supplying both modes is a named conflict, never silently
resolved. Same News artifact, same ticker builder/template, no extra ticker
keys, no news-count/sentiment/rank/trade changes. Default production builds
still do not acquire this history; live source access/activation/release are
separate remaining gates. No source-reader, extractor, template, stylesheet,
publisher, CI job, endpoint, credential or worker change is made in R9.

Proof:
- Initial history-selection cases: 29 RED on missing consumer, then GREEN.
- Source mode -> actual News writer and actual ticker loader/context/template
  exercised. The existing revision reader runs with only its byte-transport
  seam mocked; owner-valid manifest chain + raw workspace receipts yield two
  release revisions in five unique bounded byte reads. Corrupt workspace bytes
  raise the unchanged reader's integrity error before selection. No real HTTP.
- Existing release-only deduplication correctly returns one revision for two
  transcript changes with the same release; the new consumer rejects it as
  incomplete for guidance, not an unchanged outlook.
- Two different release revisions with transcript guidance also refuse; having
  two release rows is not sufficient evidence of transcript completeness.
- Expanded News/comparison/display/common suite: 297 PASS, exit0.
- Compose unchanged #7955@29dc4ce4f5b3f03ba1fc5419a507b09e1b3b93d5 and
  #7966@e963555df1d7a71ead116d641a85c07e17f84241: 405 PASS, exit0; rank-test
  and CI manifest three-way composition clean; all temporary inputs restored.
- Discriminating mutations: choose earliest instead of adjacent baseline ->
  FAIL; permit transcript guidance from release history -> FAIL after that
  test's valid baseline passed; restore -> 297 PASS. The first transcript
  mutation probe had mistakenly identical release fixture bodies and failed
  before its subject; it is explicitly discarded, not credited as proof.
- Existing CI selector includes all changed/imported reader boundaries in the
  existing earnings-release-identity gate. No CI declaration change in R9.

All data in these tests is synthetic. The work proves the reader-output-to-
News/ticker consumer path, not accepted upstream extraction, live acquisition,
independent review, merge, deployment, or production product acceptance. Old
browser captures remain old captures; no fresh browser claim or geometry change.
Remaining source ownership stays #7331/#7426, China leaf #7575 and current native
identity/rights/publication owners. Do not duplicate the source repair or invoke
the frozen native Codex401 route without evidenced authentication recovery.
