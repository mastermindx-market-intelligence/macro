# MU native acquisition: actual pre-request refusal

## Observed result

**One call to the existing Massive MU split-history producer returned `SplitEvidenceError("missing_credentials")` before an acquisition was constructed.** The native wrapper completed with exit 0 because it recorded and verified that typed refusal. This is a successful refusal witness, not a successful data acquisition, an empty provider response, an entitlement decision or a completed issuer case.

The native process was RDC **17056**, observed completed with exit **0** and runtime **8.49 seconds**. It executed the independently reviewed **18,367-byte** script with SHA-256 **6fe0f67b7335b31ef3e4a3eb9a914ac1557236689deb563ac8887b5bd2d53439**, through Python `-I -B`. The byte-exact public result is **16,454 bytes**, SHA-256 **9e9a8368a7ecfb38bcbf1f1e7ca71ae29b242aa55f4cf293492c5da472190483**. The exact launch command, wrapper, source script and original tool start/completion/read receipts accompany this report.

This result closes the uncertainty about that one execution context: the existing resolver did not obtain a usable process-environment key at call time. It does not establish whether a credential exists elsewhere in the authorised estate. A separate tracked-source check of the owner's normal environment bootstrap may identify a supported next route; no second acquisition is represented in this frozen result.

## Exact requested operation

The existing public wrapper was `engine.close_pass.massive_close.retain_split_history`, with positional arguments **MU, 2026-09-30, 2026-09-30**. The fresh, isolated private destination ended in the required `sources-massive-split-history-v1` leaf.

The intended native request was the current `https://api.massive.com/stocks/v1/splits` endpoint, ticker **MU**, `execution_date.gte=2026-09-30`, `sort=execution_date.asc` and `limit=1000`. The basis date was retained metadata; there was no upper execution-date filter. No such HTTP response was obtained in this attempt.

The [exact existing source](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_split_evidence.py) calls the resolver before producer time/UUID/page construction or transport. The [existing resolver](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/engine/close_pass/massive_close.py) checks `MASSIVE_API_KEY`, then `POLYGON_API_KEY`, at call time. No credential values were exported or printed. This source-derived explanation is distinct from independently instrumented network observation.

## Source and execution binding

The pro004 workspace remained at published **7af7a9785d74c1b420b23de3be0eac6946cc2200**. The script checked all **18** reviewed source objects against the exact current-source revision **87b01101ef13aa20ded205f3a2b267b68d094def**, the local materialized files and the workspace HEAD. It verified the protected Mastermind revision **8d838c8df453a78fac3459b7458576e1ba2cbcb8** and the previously reviewed AGENTS/CLAUDE byte identities before the call.

The script also recorded **21** repository modules actually imported by this process and checked their materialized bytes against the same workspace HEAD. This is a runtime source identity inventory; it is not a claim that every imported module was independently audited in full. The earlier 18-pin semantic review records its own full versus targeted read scopes.

The real wrapper, resolver, producer clocks, UUID generator and transport were used without monkeypatches or supplied historical clocks. Only one public producer invocation occurred. No subsequent same-artifact intake was possible, because no source artifact existed.

Postflight checks found the workspace still clean, no ignored files introduced and all 18 reviewed source pins unchanged. The fresh source leaf was absent both before and after the call. The surrounding private run directory contains the witness files; absence of the source leaf is not a claim that the wrapper wrote no evidence files anywhere.

## Result accounting

| Evidence field | Actual value |
|---|---|
| Requested vendor cases | 1: MU |
| Public producer invocations | 1 |
| Captured source cases | 0 |
| Recorded provider page/request count | Null; no acquisition/page record exists |
| Provider requests derived from the reviewed refusal path | 0, explicitly not independently instrumented |
| Provider rows, including a completed empty response | Null, not zero rows from a response |
| Actual acquisition F | Null |
| Acquisition/artifact/owner receipt/generation | Absent |
| Pinned reader receipt | Absent |
| Same-artifact intake-repeat calls | 0 |
| Source store before and after | Absent |
| Selected WP02 real cases | 0 |
| Graph1/ranking/gating/sizing/trading/prediction | Unchanged null/false holds |

The small native private result is **137 bytes**, SHA-256 **90f1ab2992c06cf7f4feb6566b0783cb1b5051b3ec2bd0b7cd8971fac37fa50c**, with null source/read/repeat results. Only its identity is included here. No provider payload was acquired or published.

The wrapper's `started_utc_ns` and `finished_utc_ns` fields are execution-stage clocks. The latter was captured before postflight/export and must not be called process termination or provider publication time. The actual process completion is the separate terminal tool receipt. The public artifact retains nanosecond integers as exact decimal strings rather than rounding them through JavaScript numbers.

## Research and authority consequence

This is now an **executed source-unavailable case** for the proposed acquisition route. It demonstrates that absence of a usable environment key is preserved honestly instead of being rewritten as no corporate actions, a synthetic positive, a historical filing observation or a selected issuer. It establishes no empirical extraction accuracy, economic relationship or forecast value.

The [accepted Massive entitlement](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/research/licenses/MASSIVE_ENTITLEMENT_RECORD.md) remains accepted. Technical availability and lawful use are different evidence fields. This failure does not reopen the global licence gate or prove account-level denial. The [dataset registration](https://github.com/mastermindx-market-intelligence/macro/blob/87b01101ef13aa20ded205f3a2b267b68d094def/config/dataset_registry.yml) remains PROPOSED, owned by macro-dashboard; no activation or source registry edit occurred.

The research axes remain **D = September 30**, **K = October 9 at 00:00Z**, and **F = null for acquisition**. Even a future successful current capture would require distinct evidence of the version public by K. This route by itself supplies no D-close price/currency, issuer-reported share count, canonical legal/class identity, complete historical population, cap ranking or owner-approved Graph1 projection.

The commissioning Sol CEO's architectural adjudication remains unasserted. Existing source/product/predictive holds and protected implementation owners remain intact.

## Independent review and next action

The independent reviewer froze a pre-result protocol, read the full exact script before execution and found no required correction. Its separate actual-result review checks the command-to-wrapper-to-script binding, original process receipts, public-file digest, refusal semantics and unchanged source identities. Reviewer code and results, including any reviewer-check correction, are preserved in their own versioned packet rather than substituted for native evidence.

Before another source call, use only an established authorised same-account environment route if the tracked source supports one, prepare its exact effect scope, and retain this original refusal unchanged. No retry is justified by pretending this run acquired data. If no such route is established, the precise next prerequisite is the existing source owner's supported runtime environment. The global diagnostic and predictive gates remain independent of that operational repair.
