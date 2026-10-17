# Treasury auction lifecycle context API (W1)

This standard-library-only module is a pure source normalizer and snapshot reader
under the existing Macro event/data owner. The existing feed builder places its
return value at `sovereign_auction_context` in `site/feeds/event_calendar.json`.
It introduces no event controller, registry, database, scheduler, network access,
risk score, trading effect, or predictive authority.

## APIs

```python
from engine.treasury_auction_lifecycle import make_observation, build_context, snapshot

receipt = make_observation(
    exact_successful_response_bytes,
    source_kind="treasurydirect_json",
    source_url="https://www.treasurydirect.gov/TA_WS/securities/announced?format=json",
    observed_at="2026-10-08T22:12:22.414829+00:00",
    metadata={"response_last_modified": "..."},
)
context = build_context([receipt], as_of="2026-10-08T23:00:00+00:00", horizon_days=30)
context = snapshot(data_dir=Path("data"), as_of=aware_datetime, horizon_days=14)
```

`make_observation(raw_text: bytes | str, *, source_kind: str, source_url: str,
observed_at: datetime | str, schema_id: str | None = None,
metadata: dict | None = None) -> dict` retains exact UTF-8 `raw_text`, its SHA-256,
decoded payload, schema, URL and caller-supplied successful receipt time. Bytes
must decode reversibly as UTF-8. Unknown/malformed source bodies are retained with
`payload=None`; consumption visibly rejects or quarantines them. The creator
never fetches, writes, or invents a receipt/publication clock. Older captures may
use an explicitly documented conservative verified-present-at upper bound.

`build_context(envelopes: Iterable[dict], as_of: datetime | str,
horizon_days: int = 30) -> dict` is pure and leaves input objects unchanged.
`observed_at` and `as_of` must contain UTC offsets. Observations later than as-of
are excluded entirely before reading their source facts, with only an exclusion
count/reason exposed. Current API `known_at` is always the selected eligible receipt time;
`first_observed_at` is the first matching selected semantic vintage within the
eligible retained inputs, explicitly qualified as local evidence rather than
public first release or complete archive history;
announcement dates, updated timestamps, record dates and HTTP metadata remain
separate. Current snapshots are not historical first-release archives.

`snapshot(data_dir: Path | None = None, as_of: datetime | str | None = None,
horizon_days: int = 30) -> dict` reads only immutable `*.json` receipt files in
`<data_dir>/treasury_auctions/observations`. `data_dir` denotes Macro's existing
data root. The default is `<repo>/data`, based on the module path; default `as_of`
is explicitly timezone-aware current UTC. Missing storage gives unavailable
context and null counts. It never writes storage. Bad files/rows stay local to
quarantine; good neighbors survive. No symlink receipt files are consumed.

## Supported schemas and failure receipt

| source_kind | schema_id | Accepted source document |
| --- | --- | --- |
| `treasurydirect_json` | `treasury_direct_json_current_v1` | Current TreasuryDirect JSON list, or exact `{"schema_id": "treasury_direct_json_current_v1", "rows": [...]}` wrapper |
| `quarterly_tentative_xml` | `treasury_quarterly_tentative_xml_v1` | Inspected `AuctionCalendar` root, named edition, StartDate/EndDate and `AuctionCalendarDate` rows; holiday nodes filtered explicitly |
| `pending_auctions_xml` | `treasury_pending_auctions_xml_v4` | Inspected TreasuryDirect namespaced `PendingAuctionData`, explicit `PendingAuctions_v4_0_0.xsd` schemaLocation and `PendingOfficialAnnouncement` nodes |

The source_kind/schema pair must agree. No migrated TAAPS JSON/XML schema support
is claimed. Unknown roots/envelopes/versions and recognized migrated fields
produce unsupported/degraded source state, never a silently empty schedule.
Original announcement/result XML adapters are not part of this patch; the
quarterly/pending adapters contain no dollar amounts, avoiding the different
legacy announcement XML amount units.

A network failure may be recorded by the existing capture owner with this minimal
receipt (no successful body or payload is asserted):

```json
{
  "receipt_version": 1,
  "status": "unavailable",
  "source_kind": "treasurydirect_json",
  "schema_id": "treasury_direct_json_current_v1",
  "source_url": "https://www.treasurydirect.gov/TA_WS/securities/announced?format=json",
  "observed_at": "2026-10-08T22:20:00+00:00",
  "error": "HTTP 503"
}
```

For a failed attempt only, `observed_at` is its offset-aware completion time; it
never yields event known-at. Failure source states remain separate from last good
observations. `source_health` groups by exact source_kind/URL and exposes the
latest attempt status/time, latest failure/reasons, last successful body receipt,
last valid observation, and valid-observation age in seconds relative to as-of.
A malformed successful HTTP body can be the last successful body receipt while
failing to become the last valid observation. Build time never refreshes age.
There is no arbitrary universal staleness threshold (`stale_after_seconds=null`);
the existing owner can apply an explicitly chosen display policy. Equal-clock
incompatible source states are visible as conflicting_source_states.

## Output and invariants

The top-level schema is `sovereign_auction_context_v1`. `decision_cutoff_utc` and
`as_of` are the snapshot decision clock; `source_observed_at` is the maximum valid
eligible source receipt clock (or null), and `asof` is its UTC date (or null). A
new build cutoff never changes source freshness. The context returns `status`,
`events`, `episodes`, `source_states`, `source_health`, compact receipt provenance,
row/file quarantine, conflicts and coverage. Original raw payloads stay in the
immutable receipt files; they are not duplicated into the feed. Each episode
preserves eligible normalized `observation_versions`, separate original-issued
and announced identifiers, true deadlines, dates and raw update metadata.

The `events` view extends each episode with Macro event fields: `type=AUCTION`,
`date`, exact `time_et` or null, `label`, source URL and `assets=["bonds"]`.
`impact=null` and `importance=NOT_SCORED` prevent scoring defaults. Every context
and row is `is_context_only=true`, `forecast_authority=RESEARCH_ONLY`, with
`probabilities=null`. No bidder-share calculation is included; existing #7320
owns that computation. JSON USD amounts remain exact decimal strings; missing,
empty, literal `null` and NaN remain null. Numeric zero remains zero. Result fields
retain semantically specific discount-rate/real-yield/FRN-margin/nominal-yield
names. No foreign-ownership, WI, financing, DV01 or stress inference is made.

Classes are Bill, CMB, Note, Bond, TIPS and FRN; conflicting explicit type/base/flag
values are withheld. There is no class/default competitive cutoff. Deadlines
come only from `closingTimeCompetitive`, localized to America/New_York on the
auction date and converted to UTC. Missing/invalid times produce visible null
reasons and never inherit the generic event-calendar 13:00 default.

Episode identities are announced CUSIP plus auction date. Original CUSIP is an
announced alias only when supported by a reopening flag and retained special
notice filename; otherwise current CUSIP is used. Distinct auction dates sharing
a CUSIP remain separate. A changed auction date cannot be joined without further
explicit official alias evidence. Tentative slots include edition, exact tuple
and source row index. Slots merge only when class, exact normalized term, auction
date and issue date uniquely match an announced episode; duplicate/ambiguous
slots remain visible. Normal coupon/FRN reopening rows may use the exact official
`originalSecurityTerm` as their schedule cohort, preserving raw current remaining
term and explicit `schedule_match_term`/`schedule_match_basis`. Bills always use
current term; unscheduled aliases into a different security do not inherit the
original cohort. Terms are never rounded to a nearest benchmark. The full Oct8
captured sample reconciles the 29Y10M Bond to its official 30-Year schedule cohort:
28 unresolved future tentative slots remain, with zero same-day unresolved slots.

`source_state` is TENTATIVE, ANNOUNCED or RESULT_OBSERVED. Actual result numeric
fields or competitive result filenames establish result evidence; endpoint names
do not. Receipt-time future-auction/before-deadline result contradictions are
quarantined. `physical_state` separately rolls a passed deadline (or fully elapsed
auction date when clock is absent) to AWAITING_RESULT. ISSUE_DATE_PASSED is a
separate calendar fact only once the ET issue date has fully elapsed;
`settled_payment_observed=null` always. A later stale tentative/announced source
cannot erase an observed result. Within the same evidence level/source authority,
the newest eligible receipt is selected; JSON takes precedence over pending XML,
which takes precedence over quarterly XML. Same-time conflicting current-source
facts withhold the episode and preserve explicit conflict evidence.

## Coverage and limits

ET upcoming date bounds are inclusive `[as_of_ET_date, as_of_ET_date + N]`.
Recently resulted bounds are inclusive `[as_of_ET_date - N, as_of_ET_date]`, plus
resulted episodes with issue dates on/after as-of ET date. The configured horizon
must be an integer from 1 to 366. Thus `N=14` includes today through today+14.
Coverage reports known upcoming, recently resulted/issue-future, unresolved
tentative, awaiting-result, holiday, exclusion and truncation counts. These are
observed-source counts, not a guarantee every future CMB is already known.
Empty available payload, failure, unsupported schema and unavailable storage are
separate states; unknown coverage counts are null, not fabricated zero.

Guards: 128 receipt files/envelopes, 2 MiB per exact source body, 8 MiB per stored
receipt (raw and decoded body duplication), 32 MiB total input, 2048 rows per body.
Truncation is disclosed and counts become null. Current snapshots select candidate files newest-first by local write mtime
(with descending filename tie-break) before the file bound. Mtime only chooses
candidates; the source bytes/digest and aware observed_at still determine source
validity and as-of eligibility. This retains recent capture files after extended
daily runs and prevents the oldest 128 receipts from permanently blocking newer
ones. File copies can change candidate priority but never knowledge clocks. All
over-bound current/historical reads disclose truncation and null coverage counts;
older historical requests must supply an explicitly selected eligible bounded
envelope set to the pure builder instead of claiming this directory scan is
complete. This patch does not garbage-collect, index or rotate receipts.

## Verification

```bash
PYTHONPATH=w1_patch python -m unittest discover -s w1_patch/tests \
  -p 'test_treasury_auction_lifecycle.py' -v
```

After integrating into Macro, run the equivalent command with the repository on
PYTHONPATH and `tests` as the discovery root. Genuine fixtures are copied verbatim
from the official source audit, with original fixture hashes and source receipts.
Tests using changed clocks or values label that synthetic receipt/adversarial
mutation; they do not pretend historical ingestion happened. The suite covers
all six classes, nonstandard/FRN times, aliases and same-CUSIP episodes, receipt
eligibility, amendments, type conflict, unsupported migration, digest/payload
tampering, good neighbors, XML holidays/joins, result regression, missingness,
physical progression, horizon bounds, immutability and bounded local loading.
