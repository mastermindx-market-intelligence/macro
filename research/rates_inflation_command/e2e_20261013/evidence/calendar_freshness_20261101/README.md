# Calendar freshness evidence — November 1, 2026

This directory records an isolated Chromium replay of the actual Events dialog, its
stylesheets, opening controller and release-publication client. It is not a
production deployment or a measurement of an agency's publication latency.

The retained public incident is cpi:2026-10-14: parser v1, published_unparsed,
data_ready false, originally detected 2026-10-14T12:31:17.596439+00:00. The replay
uses the existing governed archive repair in memory, with no canonical or
production state writes. All four CPI fields become verified through parser v2,
and the original detection timestamp remains unchanged.

Official archive:
https://www.bls.gov/news.release/archives/cpi_10142026.htm

Archive SHA-256: b9f981390c08f4a530d839495fce582124015b979bac0398bfcc35ffde0544e4.
A separate read from the real VPS using the incumbent watcher's _fetch request
path returned this exact hash, HTTP 200, 1,373,525 bytes, in 0.251 seconds.
The normal RSS request returned HTTP 200 in 0.025 seconds. A preceding probe
using a different diagnostic User-Agent failed; it is not evidence of failure
of the actual publication request path.

The UI replay uses a controlled, advancing October 14 clock. It first renders
the unparsed report, then makes the verified snapshot available. The modal node
is retained and the document does not reload. All eight theme/language/viewport
combinations passed visible hit testing without page errors; observed
snapshot-to-visible times were approximately 1.8 seconds, maximum 1796.11 ms.
These are eight controlled samples, not a production percentile or SLA.

The fixture initially omitted the dialog entrance controller, making early
screenshots blank despite DOM visibility. Those results were rejected. The
retained screenshots run the real opening controller, wait for ancestor opacity
and viewport hit testing, and were inspected in light desktop and dark Chinese
mobile views.

Client SHA-256:
5c6d1439de8c46baa97761301c51121ffebdfd0498ba623c21b60c751763c26b.

Reproduce using the sibling calendar_freshness_20261101.py script and this
directory as --out. Retained public_before.json and isolated_recovery.json make
the replay independent of subsequent production recovery. The authorized tier
is a fixture on calendar-regression.test; it never modifies a live account or
browser session.

The connected, signed-in production calendar was also opened during this
session and still displayed the exact old CPI extracting banner and Initial
Claims November 5 'in 20d'. Production recovery and final installed-code proof
remain separate acceptance gates.
