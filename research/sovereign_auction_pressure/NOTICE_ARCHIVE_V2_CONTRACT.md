# Official notice and receipt archive continuation

Operation `sovereign-auction-funding-local-codex-20261008-001`, original Codex root `01a11e6d-efdc-78a0-a489-9c1a7891df0a`. This source vertical depends on Macro #8657 at `fdc4239a67125fdbd96ddb889b3c60033f720272`. It extends the accepted lifecycle rather than replacing the collector, calendar, publisher or consumers. Source implementation is locally verified; independent acceptance, hosted checks and release remain open. All existing carriers remain Draft/HOLD.

The Chairman's live attachment and complete #8657 comment 6072718696 authorize this continuation. Protected procedure is pinned to Mastermind `732cf7be88e7159b4995a8885fbd381cd1484e3e`, compatible Skillpack v1.0.1. The new Macro source branch has its own external-SSD helper receipt `2ba5ea1a6f134981df26366e7dc3e2dd7de0542158900b4c7ac223f62a440cab`; the preceding Sol branch and retained checkout are unchanged. This branch is a stacked dependency on #8657, not a replacement main-targeted carrier.

GitHub currently identifies #6819 as Market Ontology. The program remains in `WS:RATES-INFLATION-COMMAND`; its GitHub parent issue is `UNKNOWN`. Historical records and original delivery receipts remain immutable evidence of their original state.

## Capability and source contract

- Admit only the observed TreasuryDirect v7 `AuctionData` namespace/schema pair and known flat announcement/result fields. Unsupported schema, duplicate sections, nested fields, conflicting revisions and future results are quarantined.
- `OfferingAmount` is in billions; result cash fields are in dollars. Convert using exact decimal exponents. Nominal yield, TIPS real yield and FRN rate/spread axes remain separate. Offered face is not private cash.
- Preserve issue/maturity dates, competitive and noncompetitive ET deadlines, original/announced CUSIP aliases and reopening terms. A v7 Bill with no CMB flag remains legal-class Bill with explicit unknown CMB status. Qualified TreasuryDirect JSON can identify CMB; the XML cannot manufacture that fact.
- Raw result release time has no certified timezone in the retained XML and remains raw metadata. `publication_time` stays null. Original captures lacking measured body completion keep null body receipt; no date, HTTP header or file mtime substitutes for historical first seen.
- Attended `--notice` capture accepts at most 32 unique, calendar-valid official A/R XML basenames on the existing official HTTPS hosts. It retains exact bytes and separate request, body and conservative parse/availability clocks. It registers no timer, collector or publisher.
- Receipt metadata must obey request <= body <= parse/availability when the respective clocks exist. Every admitted clock must be no later than the receipt's knowledge upper bound and decision cutoff.
- Census at most 1,024 local receipt files / 32 MiB, then exclude post-cutoff receipts before the 128-receipt projection bound. Select by receipt clocks and immutable content, never filename or mtime. Retain each origin's latest attempt and last valid receipt where capacity permits. Withhold an equal-clock revision cohort if a limit would split it. Over-limit direct streams and directory censuses fail closed.
- Truncation keeps observed facts with null aggregate coverage counts. `bounded_local_history_complete` concerns the scanned local archive only; it never certifies the official universe or historical original first seen.

## Source age policy requiring independent acceptance

`treasury_receipt_age.context.v1` uses context-display budgets of 24 hours for TreasuryDirect JSON, 8 days for pending schedules and 100 days for quarterly schedules. These are explicit display policy choices, not release cadence guarantees or collector activation. Immutable individual notices expose age without an expiring validity claim. The existing v1 `stale_after_seconds` remains null because both held strict consumers enforce that boundary. The new `context_age_budget_seconds` and `freshness_status` are producer evidence fields; current consumers may omit them until separately adopted. A stale valid source degrades context; a later failed attempt never refreshes the last valid clock or deletes its facts. Collector cadence and production adoption require their existing owners and gates.

## Evidence and remaining frontier

The thirteen retained original notice fixtures exercise Bills, Notes, Bonds, TIPS, FRNs, a CMB whose v7 subtype is unspecified, an unscheduled reopening and an exceptional noncompetitive deadline. Three new attended responses are retained under `verification/local_codex_20261008/attended_capture/`; the October 8 announcement/result and February 2025 unscheduled reopening parse successfully. Their clocks are October 9 local captures, never historical release proof.

Reproduction from the repository root:

```sh
python3 -m pytest -q --tb=short tests/test_treasury_auction_archive.py tests/test_treasury_auction_notices.py tests/test_treasury_auction_lifecycle.py tests/test_treasury_auction_primitives.py tests/test_capture_treasury_auction_observations.py tests/test_sovereign_auction_feed.py tests/test_event_calendar.py tests/test_treasury_supply.py
python3 -m pytest -q --tb=short tests/test_check_script_import_pinning.py tests/test_dag_conformance.py
```

The import/DAG run passed 59 tests. Source results and exact capture hashes are recorded in `verification/local_codex_20261008/NOTICE_ARCHIVE_VERIFICATION.json`. Pytest also reported a pre-existing cleanup PermissionError in an unrelated retained Chromium test directory; that directory was preserved.

Independent review is pending. Current Executive MCP state is read-only; an attended review routing read with subject pool `codex` and class `C2_COMPLEX_BOUNDED` returned `NONE reason=no_pool_available`, before dispatch. No review worker or native child was launched. Parent implementation continues under the no-eligible-pre-effect-worker reason; this is not independent acceptance.

Phase A remains partial: no retained official cancellation/postponement or arbitrary format-migration notice has been qualified. Disappearance from a snapshot is not cancellation. Contradictory unsupported status fields are rejected; no synthetic state transition is presented as official evidence. Full history, original release clocks, complete private cash cohorts, economic attention inputs, entitled live consumers, independent research and production acceptance remain open. SLF-006 NO-GO, D2 FAIL, Terminal KILL, `INSUFFICIENT_PIT`, null predictive outputs and the release hold remain binding.
