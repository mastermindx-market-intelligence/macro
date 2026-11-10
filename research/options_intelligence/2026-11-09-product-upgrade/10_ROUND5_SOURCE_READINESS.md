# Options — Round 5 source readiness
## Recovery milestone · 9 November 2026, America/Vancouver

**Current round status:** original packet recovery is complete; source-contract and release integration is being completed in this same round. This document will carry the consolidated round-5 findings. The canonical carrier remains Macro PR #10898.

## Original scope recovered

The exact October 21 packet was recovered by a bounded filename lookup in the authorized M2 Downloads directory. Its 189,700 bytes have SHA-256 **f08759dc8755000dcf8fcf335a1ca409fa6dd796dd757c8d29f2f3330ddba0ad**, matching the historical D86 prefix.

The archive contains 17 original members. ZIP CRC and all 16 entries in its SHA256SUMS manifest pass. The 104-task CSV and JSON round-trip identically; the exact OPT-001–104 and OPR-001–130 sets, accountable owners and linked feature/task references validate. There are 39 conditional dependency rules and 11 explicit bounded child contracts. The 440-edge union of possible prerequisite edges is acyclic.

The original files are preserved byte-for-byte under [original_2026-10-21](original_2026-10-21/). Start with its [README](original_2026-10-21/README.md), [task register](original_2026-10-21/TERMINAL_OPTIONS_EXECUTION_TASKS.csv), [parity register](original_2026-10-21/TERMINAL_OPTIONS_PARITY_REQUIREMENTS.csv) and [execution guide](original_2026-10-21/EXECUTION_REGISTER_GUIDE.md). [12_PACKET_RECOVERY.json](12_PACKET_RECOVERY.json) records exact checksums and structural validation.

This closes the **missing-original-row recovery gap** recorded in round 4. Recovery does not supply implementation or production acceptance. All 104 original task statuses remain historical PLANNED_NOT_DISPATCHED; all 130 requirements remain historical defined/not-accepted dispositions. Later scoped acceptance is retained separately.

## Immediate scope correction

The original OPT-100 first accepted vertical has 15 direct and 36 distinct unconditional transitive predecessors. It requires Market Brief, Workbench, Trade Lab, actual Save, selected-node monitoring, Monitor, outcome review, access/performance/isolation and a measured cohort usefulness result.

A selection-safe aggregate Flow → independently qualified dated Exposure → exact return increment is a useful precursor. Neither that precursor nor an ordinary saved Exposure case plus a price watch silently closes OPT-100 or OPR-129. OPT-062 retains stock/option/spread/wait comparison and conditional price-IV-time analysis with terms, quote convention, costs and mark clock; the current expiry-only Plan is a narrower asset to reuse.

The original five user jobs and the six destination labels must be mapped explicitly in the next Paper round. Original packet instructions and proposed role labels are historical planning evidence; current outer assignment, pinned source law, actual custody and release controls remain authoritative.

## Source review frontier

Affected source is bound to Terminal d15741d452403594a4ddb540a97b9a981c2a62ca and Macro e1e4552be495ea53ff804c58f76dce1500836223. Original #804 and #10866 remain on their prior held heads.

The in-progress integration addresses Flow population/quote semantics, dated Exposure domain, Volatility rank/tenor/history labels, retained Matrix wire integration, the #804/0047 migration composition, original-operation recovery, precise watch/firing semantics and the original first-release dependencies.

No application, SQL, Paper, source publisher, model activation or Fable/T3 dispatch is performed by this recovery. The same Draft planning carrier is retained. The next action in this round is to integrate the source decisions and the recovered rows into the existing masterplan and traceability projection.
