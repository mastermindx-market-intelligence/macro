# News popup upgrade — implementation and validation

Status: candidate source; production unchanged. Source baseline: macro `9af0a33eb38b08d902c3e593cb0e276d3f0d6a18`.

## Implementation

The already-live News modal now includes a compact briefing overview, dedicated official-release status, priority/context/headline filters, bilingual search, exact result counts, and native evidence disclosures. Full observations and producer limits remain outside collapsed details. Headline links allow HTTP(S) only; Jinja autoescaping remains enabled. Missing observation times remain unknown. Every valid alert remains one `data-al-row`.

The current release-publication client remains the only network owner. News snapshot alerts are excluded from incidental text/ancestor matching; publication updates go to a separate summary. The client bounds detection recency, retains old/unclocked parse failures as verification delayed, rejects source-version rollback, validates collection shapes, and uses a single in-flight request with timeout and late-response isolation. A bare readiness flag cannot establish verified facts. Missing translations retain the same claim level.

The existing shared modal handler cancels stale close teardown on reopening and retains the page opener when switching between modal surfaces. It preserves the existing access gate and owns focus/scroll lifecycle.

## Verified so far

- Original release client: 5/5 targeted counterexamples failed. Modified client: 11/11 browser regression cases pass, including partial collections, invalid/future clocks, distinct identities, empty-event fallback, contradictory readiness, and a valid newer late response arriving after a timed-out request.
- Original shared modal: rapid close/reopen and modal-switch focus return failed. Modified source fixture: 6/6 interaction groups pass, including filters/search, preserved evidence, EN/ZH changes, keyboard/reduced motion, desktop/mobile overflow, and those two regressions.
- Source rendering and available inherited client tests: 14 passed. Two generated-page/hash tests await a qualified generated-site build; they are not counted as passing.
- Native principal visual review approved desktop light/dark and mobile EN/light + ZH/dark. The complete first priority card is readable on mobile. Final width investigation identified overflow in the synthetic background tiles, not in the popup; the fixture was corrected and the browser test now checks document/body width as well as dialog content. All eight theme/locale/viewport combinations pass.
- Paid read-only contract audit: `news-popup-contract-audit-20261101-c2`, response SHA256 `db4cc9ee9e696725c09e19129ab8fc850217f7b683eddfd896d2b9382cce4e00`, reviewed/accepted as static analysis. Full-source review cleared its contingent null-target concern; targeted failures above were reproduced independently.
- Independent implementation review: `news-popup-implementation-review-20261102-c2`, retained response SHA256 `5da3d336e6c8ba1aabd068a1b9227f6922f5eeea0e04c834ffd04ee1227f7026`, fully read and manually adjudicated. Repaired findings: future build timestamps, malformed optional collections, empty events masking due rows, missing publication clocks, whitespace/missing translated facts, overly broad same-day deduplication, and committing freshness before DOM work succeeds. The contingent claim that `published=true` itself promotes unparsed documents was disproved by the full source: consumers separately inspect normalized `data_ready`. An explicit guard and regression also reject contradictory `published_unparsed` + `data_ready` inputs. Existing non-News surfaces' broader atomic reconciliation is outside this bounded change; it is not claimed repaired.

## Evidence limits and remaining gates

The source fixture uses representative synthetic data and an explicit local test access stub; it is not a signed-in production browser proof. Latin fonts initially used system fallback; CJK visual checks load the official Noto test font. Canonical visual capture, generated-page/hash integration, required CI, independent review adjudication and real served-page verification remain separate gates. No deployment or production success is claimed here.

The old held Events & News R2 PR #8186 is untouched. This candidate does not install its component or retry its held integration operation. Other News-page, provider and account/following work stays outside scope.
