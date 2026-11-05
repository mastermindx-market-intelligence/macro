# Stock publication: canonical issuer text is not a non-finite value

## Capability and exact incident

Allow the existing post-render stock-dossier guard to distinguish canonical issuer
name text from a real numeric `Infinity`, without bypassing sentinel/identity
checks or introducing a ticker allowlist. This is a bounded release-correctness
repair in the Chairman's stock-assessment recovery mission, not a signal-model
change or a replacement publisher.

The existing production render35709199694/job106740198741 on pc-render-1 reached
its stock-dossier integrity step at2026-09-23T07:23:18Z. It scanned2,736pages and
failed at07:23:29Z with9fatal matches, all the token `Infinity` inside the issuer
string `Infinity Natural Resources Inc` on INR.html: title, descriptions, issuer
metadata, OpenGraph, two JSON-LD name strings, stock-name span and eyebrow text.
Eight separate description-provenance warnings were nonfatal and are not altered.
Stockdata R2 publish and rendered-site commit steps were skipped. This run did NOT
restore published assessments and was not retried or replaced by this repair.

Base: macro@1d784190ee690959cfca62af65ab6eea766f053e.
Protected procedure: Mastermind@a5aa42d15c3e5cbfe785b415511de188cff66bd0,
compatible Skillpack1.0.1/bootstrap1. Branch: sol/dossier-canonical-name-sentinel-20260923.
Direct execution reason: CRITICAL_PATH_SHORTCUT, exact low-ambiguity guard repair.
The unrelated native UK-scope worker's refused commands are not replayed here.

## Existing owners preserved

The guard already loads canonical identity from the SAME rendered stock hub and
passes it to every check. The repair reuses that context: only the exact multiword
issuer name for the current page/ticker, in a quoted string or ordinary HTML text,
can account for an `Infinity` match. There is no company/ticker constant or page
exclusion. A bare/short/numeric-looking name gets no exception. A signed or
currency-prefixed occurrence is still a sentinel. A different or absent canonical
identity grants no exception. Other pattern classes are completely unchanged.

All original NaN/$nan*/inf/Infinity patterns and identity checks still run.
A real infinite value elsewhere on the SAME named-issuer page fails. Bare numeric
JSON, quoted numeric sentinels and malformed unquoted issuer-as-number text also
remain failures. The exception applies to a proven identity string, never to a
whole page or numeric column. Original scan counts, stale/pending rules, manifest
filter, scope, runner labels, CLI exit codes and workflow steps are unchanged.

## Evidence and limits

The test fixture reconstructs the nine reported HTML/metadata/JSON-LD contexts
from the actual failure; it is not represented as a copy of the entire production
page. The original guard fails that fixture. The candidate clears those identity
matches while planted invalid values on the same page remain failures.

Twelve new regression cases cover same-issuer text, actual invalid values, absent/
different canonical identity, short/numeric identity, malformed bare JSON, signed/
currency forms, near-match names, all other sentinel classes, HTML escaping and
end-to-end native scan identity. The focused red run was4fail; both owner suites
now pass59tests under Python3.14 and the same59under3.12 (overlapping counts).
The native test suites are already registered in existing CI; no gate is removed,
weakened, skipped or reclassified. No user-facing output text is changed.

Independent exact-source review, hosted CI, current-base release and a normal
post-render integrity/publication success are still owed. The global integration
baseline's separate126>125 scope regression remains with CI owner#6351 and is not
waived by this source fix. Restoring stock assessments is still the existing full
stock-aware producer's job. MISSION_COMPLETE:false; BUILT_NOT_PROVEN.
