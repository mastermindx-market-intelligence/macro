# China theme handoff: shape recovery and consumer dependency

Status: BUILT_NOT_PROVEN. Original carrier: Macro PR #8015.
Semantic caller: c0d2a314f08e287ede354353cc45dc4e346aa6ec.

A truthy non-object JSON root previously raised before the optional refresh
boundary. This could suppress the whole action board, including sector cards.
The repair reads theme_intel only from a dictionary. It does not change any
recommendation, eligibility, score, calendar, source date, or publication route.

The corrected regression reproduced 8 failures and 4 passing controls on e24bff53.
An initial fixture used an invalid numeric urgency; that harness was corrected
to the existing 'now' sector contract before counting the discriminating run.
The three existing owner/calendar suites then passed 128 tests with zero failures.
Logs: envelope-red.txt and owner-tests.txt. No assertions were waived.

The caller's original base lacks #7567's observation-qualified consumer.
Therefore #8015 requires #7567 for its stale/unavailable-withholding claim.
The independent EMERGING/ENTER continuation route additionally requires #8026.
Do not duplicate those rules in the caller to avoid the dependency.

handoff_proof.py runs this actual caller into the two exact consumer revisions,
using eight controlled cases each. It verifies initial/continuing entry, a
same-session HOLD correction, stale source, site-only reuse, a producer exception,
and malformed persisted data with/without refresh. All 16 cases pass; sector
cards survive every case, and theme-level entries never imply stock permission.

## Reproduce and interpret

Run from the #8015 worktree:
`python3 research/cn_prophet_audit/current_theme_handoff_20260926/handoff_proof.py`

The harness reads the pinned engine sources through Git without modifying
another branch or creating a second worktree. The local caller must exactly
match its committed bytes; the China-calendar dependency must match both
consumer pins. Producer return values are controlled fixtures, not a rerun
of the live scoring engine. Source and input bytes are unchanged by the proof.

Receipt: handoff_proof.json, SHA256
048b9b1cef1512d1ad2c6df573c6f08079a50d2f7d854aae786ce8b73806134a.
Owner-test log SHA256:
18d25811a51d5103588816f73cccb4d83f5a08b26ab946bb5cfe3222cbba3315.

This proves a bounded caller/consumer composition, not whole-repository
integration, independent review, publication, current stock buyability, or
investment performance. Keep Draft until exact-source review and the existing
release prerequisites pass. No ordinary release or data freshness gate is waived.

## Actual producer replay — recorded inputs, 2026-09-26

The synthetic composition gap is now complemented by actual scoring-engine
execution. `real_producer_proof.py` executes the unchanged #8015 caller and real
`theme_scoring.compute_theme_intel("china")`, then both exact action consumers.
No producer result, score, label, recommendation, or stock eligibility is mocked.
Each snapshot runs in a fresh Python process with only its immutable Git inputs.

Each run includes all 22 canonical themes, 280 constituent OHLCV files, the
adjusted-close panel, membership, benchmark, CN session anchor, regime/overlay
and other read dependencies. The same snapshot supplies 16 sector records,
53 cycle rows and the actual member-name loader for the mixed-board composition.

| Recorded session | Actual Semiconductors / AI Compute result | #7567 | #8026 |
|---|---|---|---|
| 2026-09-23 | EMERGING / ENTER, scores 50 / 55, clean entry false | In Favour | Buy Now, theme_enter |
| 2026-09-24 | DETERIORATING / AVOID, scores 46 / 42 | Reduce / Avoid | Reduce / Avoid |

All four target score/label/recommendation tuples match their recorded artifacts.
The new consumer does not change raw lanes or source judgments, and never grants
individual-stock entry permission. It changes the presentation of a still-open
theme entry rather than holding a genuinely deteriorated theme in Buy Now.

Snapshot receipts: `real_producer_proof_2026-09-23.json` and
`real_producer_proof_2026-09-24.json`; aggregate `real_producer_proof.json` SHA256:
`504b844184de4e9b0301309dd6091848746a428b3fb358e282102575a128c775`.

Run the two cases separately (native process caches must not cross snapshots):

```sh
python3 research/cn_prophet_audit/current_theme_handoff_20260926/real_producer_proof.py --snapshot 2026-09-23
python3 research/cn_prophet_audit/current_theme_handoff_20260926/real_producer_proof.py --snapshot 2026-09-24
```

Only the configuration root is redirected to an isolated, temporary copy of
exact recorded bytes. A transparent observer calls the real producer once and
asserts the caller returns that actual object rather than silently falling back.
A compute-time audit rejects network/process calls and writes outside that copy.
The producer's existing breadth-divergence stamping helper is not suppressed;
in these samples every extracted input, including the existing ledger, remained
byte-identical. No production source, cache, ledger or publication was changed.

Two incomplete harness preflights are explicitly REJECTED, not included in the
qualification: one omitted the CN session anchor; the next omitted native
constituent OHLCV and therefore exercised the close-only fallback. That fallback
lacks the recorded COILED_UP tape input and returned HOLD on Sep 23. Restoring the
actual 280 member files recovered the recorded ENTER judgments without changing
any engine rule. Their clearly named `*_unqualified.*` records preserve this
explanation. One unrelated stale constituent is still excluded by the native
candle loader in the qualified run; that warning was not suppressed.

This is current-code/recorded-input software qualification, not a historical
investable information set, independent review, live market advice or deployment.
Assembler clocks are injected; producer wall-date checks retain execution-date
semantics. Full-page/authenticated publication and native stock-entry integration
remain outstanding. Existing review and release gates are not waived.
