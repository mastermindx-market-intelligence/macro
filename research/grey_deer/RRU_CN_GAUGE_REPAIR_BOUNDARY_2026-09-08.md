# China gauge identity: verified defect and bounded repair

Workstream: `WS:GREY-DEER-RISK-INTELLIGENCE`; same operation and records PR #6989.
Source pin: Macro `eb9e91961ddc4f3043d0dad358602525e66eccda`.
Status: defect reproduced; proposed consumer fragment UNTESTED; production unchanged.

## Evidence that changes the prior assessment

The Chairman's screenshot discrepancy is no longer only a visual audit lead.
The summary's Deep-drawdown gauge reads `conditions.recession.score` with 60/40
thresholds (`templates/china.html.j2:2158-2163`). The real detail builder reads
`conditions.drawdown_risk.score` and its own `band` (`build_china.py:1126-1168`).
The comment asserting the two surfaces use the same recession score is obsolete.

`RRU_CN_GAUGE_PROBE_2026_09_08.py` renders the actual pinned summary fragment
and compares it with the actual builder's `_DD_READ` map. All four cases reproduced:
43 slowdown / 17 drawdown -> Elevated instead of Calm; 17 / 84 -> Calm instead of
High; 60 / 60 -> High instead of Building; missing input -> Calm instead of Unavailable.
The JSON receipt carries full source and fragment hashes. This is controlled
source/fragment proof, not a new live-browser witness or historical impact estimate.

## Exact consumer boundary

Use the existing `radar_dlg.gauges` projection already passed to the detail dialog.
Select its unique Deep-drawdown gauge, use its own score/read/tone, and demote an
absent, ambiguous or invalid observation to Unavailable. Zero remains a valid score.
Do not copy numerical thresholds into the template or change slowdown/drawdown engines.
No new store, scorer, dialog/controller, policy, authentication or navigation is needed.
The candidate uses existing tokens and bilingual read words; it does not restyle the card.

## Test and release boundary

`RRU_CN_GAUGE_CANDIDATE_2026_09_08.j2` is an uninstalled research proposal, not a
verified repair. Its expanded test-harness append was platform-blocked because the
safety status could not be determined. No retry or alternate write carrier was used.
The 29-line partial harness is preserved as `RRU_CN_GAUGE_CANDIDATE_TEST_DRAFT_2026_09_08.txt`;
it is not an executable test suite and provides no passing acceptance result.

The next lawful test must exercise the actual gauge-producer block and proposed
consumer together: all four bands, zero, independently varying slowdown, absent VM,
missing score with/without a chart, unrecognized band, duplicate gauge, missing label,
non-finite/out-of-range score, and English/Chinese parity. Preserve complete valid
reads and prove the summary cannot change merely because slowdown changes.
A missing-number detail row carrying an old qualitative label is a separate detail
consumer issue: do not claim fixing the summary alone closes every null path.

Before any source edit or release, resolve current template ownership/collision
coverage under the existing program gates. Then independently review the minimal
source change and prove the real canonical builder, publication and browser paths.
Keep #6685 and the Macro Command rebuild with their incumbent owners. The record
package neither grants source takeover nor removes any release hold.
