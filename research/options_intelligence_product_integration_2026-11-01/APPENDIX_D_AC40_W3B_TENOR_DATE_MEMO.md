# Appendix D — AC40 tenor date semantics (W3B): decision memo for the seat

Status: OWNER_ADJUDICATION_OPEN → orphaned. The seat rules. ORCH-2 takes no owner decision.

## 1. The question and who owns it

| Fact | Class | Locator |
|---|---|---|
| The question was posted by `mastermindx-2` at 2026-10-30T15:44:09Z on merged Terminal PR #1104 (W3 term structure). | observed | mastermind-terminal PR #1104, issuecomment-6526883926 |
| PR #1104 was authored by `mastermindxryan` on branch `claude/options-r1-w3-term-1021` and merged 2026-10-22T09:48:37Z. | observed | PR #1104 metadata |
| No comment has answered it on #1104 since it was posted. | observed | #1104 comment list, read 2026-11-01 (§L5 facts) |
| W3B is not in the Options ledger at all, so no other carrier holds the answer. | observed | ledger grep "W3B" = 0 hits |
| The owner is the R1/W3 program author. That is a historical PR author, not a live writer, so under leadership continuity the current receiver (the seat) rules. | interpreted | CLAUDE.md leadership-continuity ruling 2026-10-24 |

## 2. What the code does and what the copy promises

ORCH-2 read every file below directly. The L5 Fabric lane oi2-l5-r1 was burned on a temperature refusal (DEVIATION). Terminal is at db6168c2 and Macro at 820f33b5. The blob shas were recorded with `git hash-object`.

| # | Fact | Class | Locator |
|---|---|---|---|
| F1 | The producer DTE clock is the payload `asof`. It sets `today = pd.Timestamp(asof).date()` and `dte = (exp_dt - today).days`, and drops expiries with `dte < 0`. `asof` is "the latest available greeks date", and the same value is published as `"asof"`. | observed | macro `engine/options_hub.py:184,188-189,226` @820f33b5 (blob aada8be9); unchanged at c133b698 L188 |
| F2 | Terminal reads that payload as-is: `VolTermRow { dte; exp; atm_iv }`. | observed | `terminal/components/vol/volTypes.ts:14-18` @db6168c2 (blob bf25665f) |
| F3 | The interpolation math runs on the producer `dte`. `constantTenorPoint` brackets the target with `lo.dte < tenorDays < hi.dte` and interpolates `iv²·dte` linearly. So "7D" means 7 calendar days after `asof`. | observed | `terminal/lib/volTenorComparison.ts:64-95` @db6168c2 (blob 38cfe55c) |
| F4 | The date on an interpolated row comes from a different clock: `exp: addDays(todayIso, p.tenorDays)`. Here `todayIso = today ?? etToday()`, and `etToday()` is the viewer's browser clock in America/New_York. | observed | `terminal/components/vol/VolComparePanel.tsx:43-51,115,147` @db6168c2 (blob 8894ce34) |
| F5 | The production mount passes no `today` prop: `<VolComparePanel term asof selectedExp lang sessionsOld spot events …>`. So F4 always uses the browser clock in production. | observed | `terminal/components/vol/VolView.tsx:547-555` @db6168c2 |
| F6 | The copy promises interpolation stays between the supplied expiries. EN/ZH `cmpTermFoot`: "Interpolation is variance-linear in calendar days between the two nearest supplied expiries; nothing is extrapolated outside them." `cmpStripBasis` says "Clock {date} nightly". | observed | `terminal/components/vol/volStrings.ts:226-229,254-257` @db6168c2 (blob 29e8b506) |
| F7 | Supplied rows keep their true exchange expiry (`exp: row.exp`). Only interpolated rows carry the shifted date. | observed | `VolComparePanel.tsx:138-141` vs `:143-149` |
| F8 | The defect appears on any day the viewer's ET date differs from `asof`. The counterexample below shows a 7-day gap; even a 1-day gap shifts every interpolated date by one day. The expected-move path is separate and declares its two clocks (`tradingDaysBetween(todayIso, selectedExpiry)`, L195-202). It is not part of this question. | calculated | F1 + F4 + F5 |

Consequence: the premise for option B is now proven. The producer DTE anchor is `asof`, so `addDays(asof, tenorDays)` would put the date on the same clock as the math (F1, F3). Option B therefore needs no further factual work; only a ruling.

### The counterexample, recomputed (calculated)

The snapshot is dated 2026-10-23. It supplies a 4D expiry on 2026-10-27 at IV 40% and a 10D expiry on 2026-11-02 at IV 30%. Interpolation runs in total variance, w = σ²·T:

- w(4) = 0.40² × 4 = 0.640
- w(10) = 0.30² × 10 = 0.900
- w(7) = 0.640 + (0.900 − 0.640) × (7 − 4)/(10 − 4) = 0.770
- σ(7) = √(0.770/7) = 0.331662 → 33.166247903554%

This matches the figure in the comment, so the arithmetic is not in dispute. The dispute is about which clock the date uses:

- The tenor axis (4D, 10D, 7D) is measured from the snapshot, 2026-10-23. Seven days after the snapshot is 2026-10-30.
- The row's date is `today + 7`. Viewed on 2026-10-30, that is 2026-11-06.
- So the row mixes two clocks. The date it shows is four days past the latest expiry that was actually supplied (11-02), and the 4D expiry it interpolates from (10-27) had already passed when it was viewed.
- Meanwhile the copy says interpolation stays between the supplied expiries.

The rule this breaks is "stale is never live": a snapshot from seven days earlier is presented as a horizon measured from today.

## 3. Options

| Option | What changes | Truth after the change | Cost / risk | Who acts |
|---|---|---|---|---|
| **A. Declare it intentional and qualify the label** | Rename the column for interpolated rows (e.g. "horizon from today"). Add a footnote giving the snapshot date. Remove the claim that interpolation stays between supplied expiries. | Still mixes clocks. The 7D-from-snapshot variance is shown against a today-anchored date, and nothing makes that truthful once the snapshot is ≥1 day old. | Copy-only, but it leaves a semantic error behind honest-sounding words. | Terminal copy owner |
| **B. Anchor interpolated dates to the source clock** | Interpolated date = snapshot (or the producer's DTE anchor) + tenorDays. Rows whose date is before today are labeled historical/stale. A missing asof means no date is shown, with the reason. | Consistent with both the copy and the math: the producer DTE clock is `asof` (proven, §2 F1). | A small Terminal code change plus tests: fresh, old and missing-asof snapshots × supplied/interpolated/unsupported rows × EN/ZH. Its factual premise is proven (§2 F1). The expected-move two-clock path must stay untouched. | Terminal implementer, after the seat rules |
| **C. Show no calendar date on interpolated rows** | Interpolated rows show the tenor only ("7D constant-maturity, interpolated 4D→10D, snapshot 2026-10-23"). Supplied rows keep their real expiry dates. | Makes no clock claim, so it cannot imply a supplied expiry it is not. That satisfies the AC40 falsifier directly. | The smallest change: one render branch plus copy in EN/ZH. It loses a convenience date. | Terminal implementer |
| D. Hide interpolated rows when the snapshot is ≥1 day old | Suppress the rows. | Truthful but lossy. Fresh snapshots keep the defect at day 0 only if the clocks differ intraday. | It removes evidence instead of qualifying it. Not recommended. | — |

## 4. Recommendation (interpreted; the seat rules)

**B, with C as the acceptable minimal alternative.** Option B's premise was the open condition, and it is now proven: the producer DTE anchor is the payload `asof` (§2 F1).

- **Why B.** It puts the date on the same clock as the variance math (F1, F3). It makes the existing copy true as written (F6). It keeps the convenience date, and the accepted interpolation math stays DO_NOT_REDO.
  - Concretely, the interpolated date becomes `addDays(asofDate, tenorDays)`.
  - A date before the viewer's ET today is labeled as past ("before today · from the {asof} read").
  - When `asof` is missing, no date is shown, with the reason `cmpClockUnstated`.
- **When to choose C.** The seat may prefer to make no calendar claim on a constant-maturity point at all. C is smaller (one render branch plus EN/ZH copy) and equally truthful. It drops the date.
- **A is rejected.** It relabels the error rather than removing it.
- **Discriminating tests for either B or C:**
  - asof 2026-10-23 viewed at a pinned `today` of 2026-10-30. For B, the 7D row reads 2026-10-30 and is labeled past. For C, it shows no date.
  - asof equal to today. B shows the same dates as today's code; C shows none.
  - asof missing.
  - supplied rows unchanged.
  - unsupported rows unchanged.
  - EN/ZH parity.
  - the expected-move two-clock line unchanged.

## 5. Consequences of each ruling

- **Ruling C or B:** this is ordinary reversible Terminal work. It goes on its own branch under a fresh Fabric build/review pair, and leaves the Exposure, Save and P09 surfaces untouched.
  - Acceptance follows the original W3B criterion: fresh and older snapshots, missing asof, supplied/interpolated/unsupported rows, both languages, and the three IA viewports.
- **Ruling A:** a copy-only change. It still needs an explicit footnote that the IV is snapshot-relative. AC40 stays falsifiable by the same counterexample.
- **No ruling:** AC40 stays GATED (owner adjudication). The counterexample keeps reproducing for any snapshot viewed after its own date.

## 6. Seat ruling (2026-11-01)

**The seat ruled Option B.** Source: [https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1104#issuecomment-6556677418](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1104#issuecomment-6556677418) (Options Intelligence completion seat, ruling under leadership continuity on the unanswered question 6526883926). This section transcribes the ruling; ORCH-2 decided nothing.

Rule points, as ruled (point 2 as clarified):

1. **Interpolated date = asofDate + tenor.** When `asofDate` is a valid ISO day, an interpolated row's date is `addDays(asofDate, tenorDays)` (today `VolComparePanel.tsx:147` uses `addDays(todayIso, tenorDays)`).
2. **Past label (as clarified).** The ruling ([issuecomment-6556677418](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1104#issuecomment-6556677418)) said "before the viewer's ET today", but its first acceptance case (asof 2026-10-23, today pinned to 2026-10-30) expects the 2026-10-30 row to be labeled past. The seat's clarification ([issuecomment-6556853817](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/1104#issuecomment-6556853817)) settles the boundary: an interpolated row is labeled when its date is **on or before** the viewer's ET today, and only a date after today stays unlabeled. The label names the read date and must be true at the boundary, so it cannot say "before today", which is false for today's own date. Wording such as "not ahead of today · from the {asof} read" fits, with EN and ZH matching. Acceptance case 1 stands. The example wording "before today" in §4 is superseded by this clarification.
3. **No date when asof is missing.** When `asof` is missing or invalid, interpolated rows show no calendar date, and the reason is stated in EN and ZH.
4. **calDte on the same clock.** The skew fallback `calDte` (`:208`) counts from `asofDate` when it is valid, and falls back to `todayIso` only when `asof` is missing; that fallback is declared.
5. **Unchanged list.** Supplied rows, unsupported rows, the accepted interpolation math (DO_NOT_REDO), the expected-move line (`:195-202`) and the events-inside-the-curve windows (`:220-228`) stay as they are.

**A is rejected**: it relabels the error instead of removing it. **C is not chosen**: it is truthful but drops a true and useful date.

Status: **RULED, build pending, not ACCEPTED.** The Option B build will land on its own Terminal draft PR from master and will need an independent non-authoring review before it can be marked ready. The ruling's acceptance cases are the discriminating tests listed in the §4 bullets ("Discriminating tests for either B or C"). The three IA viewports in the acceptance criterion come from §5.

Build obligation: no Option B build exists yet. The build must implement the on-or-before rule and the boundary-true wording, with a RED-first test that pins the equal-to-today case, and it must name the rule in its PR body.

