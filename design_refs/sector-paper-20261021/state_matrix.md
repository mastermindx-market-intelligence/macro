# Sector Paper 2026-10-21 — board × state matrix

Data-state matrix for the Sector Intelligence completion boards (masterplan §7.2:
"Meaningful examples for normal, partial, zero, empty search, loading, stale,
incompatible generation, invalid payload, offline, unauthorized, locked, uncertain
command and corrected-record states"). Base commit `3d8d14acdc8d`. Companion file:
`state_matrix.csv` (authoritative, 102 rows = 6 boards × 17 states).

**How to read a row.** `applies=no` means the state cannot occur on that board; the
`tier1_render` cell carries the one-line reason and every other column is `n/a`/`none`.
`trigger_code` names the real code condition `file:line` that produces the state today,
or `NOT YET PRODUCED` when no code condition exists. `status` is `PRODUCED` exactly when
a `file:line` trigger exists. `tier1_render` is the Tier-1 treatment the Paper writer
draws (≤ 20 words); where code already renders the state, the treatment quotes that
render; where it does not, the treatment is the required design.

**Board → current-code surface.**

| Board | Current code that carries its states |
|---|---|
| brief | `templates/_sector_central_brief.html.j2`, `_sector_central_brief.js.j2`, `_sector_central_coverage.js.j2`; SI Overview hero/calls/watch in `templates/sector_central.html.j2` + `templates/_us_act_now_board.html.j2` |
| explore | `templates/sector_central.html.j2` six views (map/moving/money/explore/confluence) + `templates/subsectors.js` |
| dossier | `templates/subsector_detail.html.j2` (Signals/Drivers/Companies/Evidence) + Record via the measured-read panel |
| research | `templates/_sector_prophet_context.js.j2` (Sector → Prophet/Screener continuation receiver); the editable composer itself is U08, not yet built |
| watches | `templates/watchlist.js` (account-owned watch/save owner, sync chips) + observational strips (`_us_bottoming_watch.html.j2`, `desk_watch.js`) |
| cycles | `templates/sector_cycles.html.j2` + `templates/sector_cycles.js` (+ `engine/sector_cycles.py`, `engine/cycle_ontology.py`) |

**Semantics law (binds every board).** Locked uses the violet lock treatment only —
"never violet; violet is lock-only estate-wide" (`templates/theme.css:2236`; locked-content
ghost recipe `blur(5px) saturate(.35) opacity .42` at `templates/theme.css:2751`); no
colored left edge or accent stripe on any container. Direction ink rides `--up`/`--down`,
which swap under `html[data-lang="zh"]` (`templates/theme.css:277-278`); health, severity
and staleness ink never flips — the zh remap touches "ONLY the pole tokens, ONLY inside
these gauge scopes", so every health/severity/staleness signal keeps red=bad
(`templates/theme.css:548-554`). An uncertain command shows the command's last known
state and disables re-issue until reconciled, never an optimistic success
(`templates/watchlist.js:189` is the existing acknowledgement law). Unknown is never
shown as zero (`templates/subsector_detail.html.j2:124`, `sgn`).

## brief

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/_sector_central_coverage.js.j2:53` | 'N of 11 sectors have qualified measurements' + evidence date |
| stale | `templates/_sector_central_coverage.js.j2:87` | 'Older than source page <date>' appended; numbers stay |
| incompatible_generation | `templates/_sector_central_coverage.js.j2:52` | clock_mismatch: dates disagree, no coverage asserted |
| partial | `templates/_sector_central_coverage.js.j2:85` | 'N of 11 measured'; unmeasured named in full evidence |
| error | `templates/sector_central.html.j2:3023` | 'Data failed to load — please refresh.'; preview stays |
| empty | `templates/sector_central.html.j2:2092` | 'Refreshing the action board — check back after tonight's close.' |
| no_access | `templates/_us_act_now_board.html.j2:64` | free shell: preview rows only, full-board counts |
| loading | `templates/_sector_central_brief.html.j2:15` | placeholder copy until matching closes land |
| offline | `templates/sector_central.html.j2:4156` | shell stays exactly as rendered; no flash |
| unauthorized | `templates/sector_central.html.j2:2030` | 401/403 no-op; sign-in disclosure line stays |
| locked | `templates/_us_act_now_board.html.j2:31` | violet lock; 'N more here — sign in' per lane |
| invalid_payload | `templates/_sector_central_coverage.js.j2:31` | 'coverage could not be checked — open the full evidence' |
| zero | `templates/_sector_central_coverage.js.j2:78` | '0 of 11 sectors have qualified measurements' |

## explore

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/subsectors.js:508` | 'as of <date>' per universe; honest coverage line |
| stale | `templates/sector_central.html.j2:1655` | >12h guard demotes token to 'LAST SESSION · SETTLED' |
| incompatible_generation | `templates/sector_central.html.j2:3816` | 'History is from a different day … Not drawn, never mixed' |
| partial | `templates/sector_central.html.j2:3621` | 'Partial — N of 11 measured' chip |
| corrected | `templates/sector_central.html.j2:1973` | 'Comparison reset after a source change' |
| abstained | `templates/sector_central.html.j2:3895` | 'Forecast: none — no forecasting model has been approved' |
| error | `templates/sector_central.html.j2:3746` | 'History unavailable right now' + 'current read unaffected' |
| empty | `templates/subsectors.js:506` | 'No data yet — run the nightly build.' |
| loading | `templates/sector_central.html.j2:3741` | true-geometry skeletons + 'Loading history…' |
| offline | `templates/sector_central.html.j2:2032` | 'could not be loaded', distinct from denied/invalid |
| unauthorized | `templates/sector_central.html.j2:2030` | 'Sign in with access to view these observations.' |
| invalid_payload | `templates/sector_central.html.j2:2040` | 'could not be verified' (schema gate `basket_pulse.v1`) |
| zero | `templates/subsectors.js:309` | 'Nothing extended or in a downtrend right now' |
| empty_search | `templates/subsectors.js:496` | count-only '0 / N' header; no no-results copy yet |

## dossier

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/subsector_detail.html.j2:163` | 'as of' pill; coverage; freshness/method/reliability grid |
| partial | `templates/subsector_detail.html.j2:156` | priced / total members; thin pill under six priced |
| error | `templates/subsector_detail.html.j2:214` | chart mount fails console-only; page keeps working |
| empty | `templates/subsector_detail.html.j2:196` | 'Member detail is unavailable for this group.' |
| loading | `templates/subsector_detail.html.j2:59` | chart host reserves 420px true geometry |
| zero | `templates/subsector_detail.html.j2:124` | zero renders '+0.0'; null renders '—' |

## research

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/_sector_prophet_context.js.j2:26` | subject chip + dated note + return href; Screener armed |
| error | `templates/_sector_prophet_context.js.j2:76` | 'Screener unavailable … still return to the sector's evidence' |
| empty | `templates/_sector_prophet_context.js.j2:23` | no `si_sector`: strip hidden; Prophet standalone |
| loading | `templates/_sector_prophet_context.js.j2:49` | Screener button disabled until source mounts |
| invalid_payload | `templates/_sector_prophet_context.js.j2:25` | 'Selected sector unavailable … Prophet remains available' |

## watches

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/watchlist.js:851` | 'Saved to your Mastermind account' / 'Up to date' chip |
| partial | `templates/watchlist.js:1036` | one failed ticker degrades exactly its drawer |
| error | `templates/watchlist.js:866` | 'Change not saved … will not sync on its own. Please retry.' |
| empty | `templates/watchlist.js:66` | 'Your watchlist is empty. Search above to add a holding' |
| no_access | `templates/watchlist.js:872` | 'Portfolio unavailable — read-only'; edits paused |
| loading | `templates/watchlist.js:857` | 'Saving…' chip; nothing blocked while it finishes |
| offline | `templates/watchlist.js:863` | 'Offline — changes kept locally'; written through later |
| unauthorized | `templates/watchlist.js:860` | 'Local to this browser — save it to a free account' |
| invalid_payload | `templates/watchlist.js:183` | unparseable blob falls back to defaults, no crash |
| empty_search | `templates/watchlist.js:435` | book-empty copy names which book and what to do |
| uncertain_command | `templates/watchlist.js:189` | acknowledgement only after the write lands; never optimistic |

## cycles

| State | Trigger | Tier-1 render |
|---|---|---|
| fresh | `templates/sector_cycles.js:1529` | 'Sector rotation · <asOf>' header; cards/legs/hazards drawn |
| stale | `templates/sector_cycles.js:1306` | amber/red 'curated <N>d ago' badge; engine read stays |
| partial | `templates/sector_cycles.js:1458` | 'What drove this move — research pending' |
| corrected | `templates/sector_cycles.js:1332` | 'revised <date>: <summary>' provenance line |
| abstained | `templates/sector_cycles.js:1077` | hazard PRIOR badge, muted; badge never omitted |
| error | `templates/sector_cycles.js:2052` | failed rotation fetch silently drops chips; no error UI |
| empty | `templates/sector_cycles.js:1435` | 'No major turns in window.' |
| loading | `templates/sector_cycles.js:2001` | core paints; heavy series hydrate after first paint |
| invalid_payload | `templates/sector_cycles.js:19` | payload absent: board never mounts; no typed UI |
| zero | `templates/sector_cycles.js:1546` | 'No sectors are at prime entry right now.' |
| empty_search | `templates/sector_cycles.js:1803` | rows/groups hidden; no no-results copy; All/Clear offered |

## Not yet produced

Actionable gaps (`applies=yes`, no code condition today — do not draw these states as
triggered until the trigger exists):

- **corrected** — brief (R3A-92 producer-dependent gap); dossier (Record provenance);
  watches (record-owner dating); research (snapshot revisions). Cycles already produces
  a narrative-revision note (`templates/sector_cycles.js:1332`); explore already produces
  the interval baseline-corrected reset (`templates/sector_central.html.j2:1973`).
- **stale** — dossier (no freshness threshold on the detail page); research (no snapshot
  clock on the handoff).
- **incompatible_generation** — cycles standalone (reads raw rotation/fragmentation with
  no generation guard, C20/U02); dossier (member/signal generation join); research
  (changed-source-generation at the receiver). Brief covers its date-coherence case via
  `clock_mismatch`; explore already renders the withheld-history note.
- **abstained** — dossier Record (Neutral/abstention share not separated from the
  ambiguous hit metric, C23/U04).
- **offline** — dossier; research; cycles (no offline UI; C28/U11).
- **invalid_payload** — dossier (no shape guard on the inline detail JSON).
- **no_access / unauthorized** — research (missing/expired evidence access; account
  fencing at the receiver, U08).
- **partial** — research (the 'no Sector evidence attached' disclosure while only ETF
  and question were passed, §8.2).
- **zero** — research (Screener zero-match must explain the actually loaded universe).
- **uncertain_command** — research (pending save/submit with uncertain outcome; J10).

Structurally non-applicable (`applies=no`, 23 cells): search/command-free boards
(brief, dossier, cycles have no search; brief, dossier, cycles issue no mutating
commands), un-gated boards (explore/cycles payloads public; no locked surface outside
the Act-Now gate), watches' symbol-store model (no generation joins, no calls, zero ≡
empty), and research's no-claims composer (nothing to abstain from). Full reasons are
in the CSV rows.

## Cross-board rules

**Loading.** Loading is a true-geometry state, never a blank or a spinner over nothing:
the surface reserves the geometry the content will occupy (`.skel mr-skel-line` /
`mr-skel-row` line/row skeletons at `templates/sector_central.html.j2:2207-2209`, the
420px chart host at `templates/subsector_detail.html.j2:59`) and the useful core paints
first while optional depth loads (cycles' split core/series payloads,
`templates/sector_cycles.js:2001`; the cycles SSR as-of starts as an ellipsis until JS,
`templates/sector_cycles.html.j2:45`). Loading is announced politely, must never
resemble empty (a still-loading list is not "no data"), and must never trigger a side
effect — research's contract explicitly forbids loading-induced automatic saves (J10).

**Stale.** Stale qualifies the answer, it never replaces it: the answer and its numbers
stay, and an amber chip beside the as-of carries the age (brief's 'Older than source
page', cycles' 'curated <N>d ago' amber/red TTL badge, explore's 'LAST SESSION ·
SETTLED' demotion after the >12h guard at `templates/sector_central.html.j2:1655`; the
engine-side >48h rotation guard keeps conviction ordering,
`engine/sector_central.py:677`). A stale source is never relabelled live, dates are
never rolled forward to look fresh, and staleness is data-quality ink (never flipped
under ZH), announced politely.

**Incompatible_generation.** When two sources were generated on different days, the
join is withheld whole, not blended: explore renders 'History is from a different day —
history X, current read Y. Not drawn, so the two are never mixed'
(`templates/sector_central.html.j2:3816`, produced by
`engine/leadership_rotation_context.py:1629/1785/1798`). The board keeps its
same-generation content and names both dates; it never backfills the older source into
the newer snapshot, and never treats the withheld half as zero or empty. The 19 Oct /
16 Oct rotation case in the masterplan is exactly this state doing its job.

**Corrected.** A correction is a dated provenance event, not an overwrite: the original
value or narrative stays visible with a 'revised <date>: summary' note beside it
(cycles' revision provenance, `templates/sector_cycles.js:1332`; explore's 'Comparison
reset after a source change' when a baseline was corrected,
`templates/sector_central.html.j2:1973`). Corrections come only from the record owner —
no board invents a correction marker where the native source has no correction contract
(R3A-92), ordinary daily change is never labelled a restatement, and a corrected record
never silently replaces what a user previously read.

**Abstained.** Abstention is an explicit, separately-counted outcome, never a zero and
never silence: cycles shows a muted PRIOR badge wherever a hazard cell did not pass the
W4.2 gate (the tooltip names the KM base-rate prior explicitly; badge never omitted),
explore prints 'Forecast: none — no forecasting model has
been approved', and the grader's Neutral rows must appear as their own share apart from
conditional directional accuracy (C23/U04 — dossier Record, still to build). No board
folds abstentions into a denominator, and no blended confidence badge covers them.

**Locked.** Locked means "here, not yours yet": the violet lock treatment only
(`templates/theme.css:2236`, `2751`), preview rows plus a per-lane 'N more here — sign
in to see the full lane' line (`templates/_us_act_now_board.html.j2:31`), with
full-board lane counts preserved because counts are free while names are paid (R3A-03).
The shell is computed from the identical source list as the payload so the two cannot
disagree (R3A-15); a fetch failure keeps exactly this shell (`templates/sector_central.html.j2:4156`)
— never a blank board, never a flash of protected rows, and never a red/error treatment
for what is an entitlement state.

**Uncertain_command.** A command whose outcome is unknown shows the command's last
known state and disables re-issue until the effect is reconciled on the same carrier —
never an optimistic success and never a silent retry through another path. The estate's
existing law is the watches acknowledgement contract (`templates/watchlist.js:189`: the
write itself is the acknowledgement; a pre-write optimistic state is not one, and
near-misses never emit), plus the typed failure chips that say what was not stored and
ask for an explicit retry (`templates/watchlist.js:866-874`). Research save/submit must
inherit exactly this shape (J10); boards that issue no mutating commands never render
the state at all.
