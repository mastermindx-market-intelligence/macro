# Factor Atlas — held Macro retained-minute decoder ABI conformance

**Read-only interop research. No admitted source, live capture, raw tape, new revision selection or production reader.** The complete reference is Macro [PR #8623](https://github.com/mastermindx-market-intelligence/macro/pull/8623), exact source head `6cff6ef8aba28dc7ee6f7779a81ef18856d9b3b6`, original file `engine/entry_radar/replay/terminal_minute_observations.py`, Git blob `95b53bba32eb2ebd6e7804052c31271bf1b65eed`. This proposed owner source remains DRAFT/UNMERGED; no installed reader/selection, source rights, monetary basis or current data availability was established.

## Exact owner-visible ABI and non-admission

The incumbent reader's public `decode_terminal_minute_observations` returns schema `mastermind.entry_radar.terminal_minute_observations.v1` and a list of versioned rows only when original source captures are read with their enrolled **reader receipts**. Per row it supplies original event `start/end` ISO UTC clocks, source `revision_id`, `known_at` from conservatively ceiled reader nanoseconds, observed close and optional volume, source response/capture-prefix hashes, reader receipt SHA-256, page/row indices and request/response adjustment role declarations.

That original proposed reader explicitly leaves `basis_id: null` and `basis_refusals: [TERMINAL_BASIS_UNPROVEN]` on **every** emitted source row. Neither `request.adjusted=false` nor response page `FALSE` proves a corporate-action-adjusted monetary basis; a decoder's locally consistent SHA-256 does not authenticate who held the source file or the original rights. The reader does not pick a winning revision. Its partner source/calendar/rights owners and canonical selector are authoritative; the Factor Atlas Session 2 work cannot upgrade any of these fields on its own.

## What is newly native and tested

`prototype/owner_reader_abi.py` is a pure **negative-qualification interoperability check** for that exact candidate format. It reads no file and makes no API call. On a supplied *already-decoded* mapping, it checks:
- Exact decoder schema, status `REVISION_INPUTS_BUILT_NOT_ADMITTED` or empty `UNAVAILABLE`, a closed authority mapping and the retained explicit monetary-basis refusal.
- Each row's self-consistent canonical JSON digest, capture hash/page/row source ref, source and reader receipt nanoseconds, ISO UTC minute identity, reader nanosecond ceiling to the earlier reader's microsecond precision, explicit external calendar window, signed/finite close and observed/zero/missing/null volume states.
- Whether the source provided an explicit security ID within the caller's four-name scope, rather than silently constructing a canonical listing identity from a ticker. It cannot infer a PIT listing by itself.

It maps source-shaped values into the *existing* `source_preflight.MinuteClaim` without inventing any missing authorities: `listing_ref=null`, `basis_id=null`, `basis_receipt_sha256=null`, `action_vintage_ref=null`, `volume_convention_ref=null`, `selection_receipt_sha256=null`, `rights_ref=null`, `dataset_use_ref=null`. A source response/page SHA-256 remains a content-bound evidence *claim*, not an entitlement or true source-package attestation. The existing preflight returns explicit refusal reasons and a real missing/unknown expected population count. All mapped candidates return **`OWNER_BASIS_UNPROVEN`** or **`OWNER_READER_UNAVAILABLE`**, `market_pilot_admitted=false`, no publication, all five authority flags false, and NO factor `WindowPressure` output.

If the original source owners later prove split/volume basis and release an authentic admitted packet, its ABI and owner-selected revision conditions must be refreshed and independently accepted. This research check must not be patched to trust a user-controlled `basis_id` field on today's held v1 decoder.

## Exact evidence and limits

The new `prototype/test_owner_reader_abi.py` exercises **27** fictional source-reader rows: complete 12/12 still refuses basis, all-missing, partial cohort, real nanosecond read ceiling, stale/after-cutoff readers, source/reader ordering, null/missing/explicit-zero volume, chart-adjusted capture, changed timestamps and self-consistent SHA receipts, damaged capture references, unsupported decoder versions, duplicate revisions and forged authority. No service, actual raw file or real source reader was executed. The original code's owner-side receipt/checksum contract is used only as *source-attributed public interface evidence*, not copied implementation.

The existing GitHub Actions dedicated research fixture workflow explicitly lists **13 suites** and ran **384/384 local Python 3.12 synthetic tests**, comprising the preceding 357 verified cases plus 27 new ABI-conformance cases. The hosted verdict for this new source head must be consumed independently. The original Terminal [PR #844](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/844) and Macro #8623 remain original held source carriers; no source writer or runtime was transferred and no data/quote/trade feed was activated.

Prior explicitly platform-denied four source reads, benchmark edit and current-base compatibility comparison, plus the separate denied S2-P4 downstream read-model patch, remain held and were not retried through another mechanism. This ABI inspection is a distinct *source-output schema conformance* capability, not an alternate method of obtaining those denied source contents or code changes.
