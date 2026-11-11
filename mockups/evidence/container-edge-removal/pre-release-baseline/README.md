# Production baseline before rail-removal release

The three normal public HTML pages and 19 reachable resources match main `54b903f7b45ddf8000a8ab432d6ac1edd63be896` exactly. One stylesheet, `/risk_radar_workspace.css`, returned HTTP 401. The raw baseline result is retained as **22 of 23 matches**, not a complete pass or acceptance of the new design.

Committed access rules omit this path from the public asset list and route protected assets through registration. This is consistent with the observed response; it does not establish an explicit product decision that this specific stylesheet should be gated, or prove the deployed denial layer. No authentication, entitlement, access configuration or product source was changed.

Post-release byte proof may supply this receipt using `--access-limits` to preserve the known boundary without re-requesting it. The receipt binds the earlier observation and current expected Git bytes separately. `passed` stays false for incomplete closure; `public_resources_passed` describes only attempted public resources, and exit code 3 identifies this bounded partial proof. Browser evidence must likewise distinguish actual public interactions from inaccessible member content.
