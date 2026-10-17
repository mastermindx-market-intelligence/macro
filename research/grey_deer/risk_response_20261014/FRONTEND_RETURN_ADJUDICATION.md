# Frontend return — verified integration with parent repairs

Original root/parent: `macro-risk-response-20261014-c1`.
Child: `risk-response-partial-ui-20261015-c1-01`, C1_ROUTINE_BOUNDED fix_build.
Normal routing: GLM glm-5.3-flash / ubuntu0; original controller PID73121.
Same-ID result: TERMINAL/rc0,3473bytes, retrieved and consumed.
Retained stdout SHA256: `4c767db2741bd38469d6718eac9d22f8032185df631bc7efbeeb7cfb3a6972cd`.
Advertised patch:12754bytes, SHA256 `78f1fdaf2e96cb71890330b82979869504f041fb97a59fb549b5a6c0d8905dad`.

## Artifact delivery and application

The first export into the repository research directory was refused before destination reservation (`destination_outside_approved_evidence_root`). Read-only inspection of the installed artifact owner established its explicit approved staging root `/Volumes/Mastermind/evidence`. No setting or permission was changed. The same run/root/parent/host/stdout hash was exported through the same adapter into `/Volumes/Mastermind/evidence/macro-risk-response-20261014-c1-frontend-return` with COMPLETE/RETRIEVED, matching advertised bytes/hash and `execution_replayed=false`. This corrected destination precondition is not a new worker or carrier. The manifest does not attest unrelated historical worker bytes.

Parent verified the exact file hash and all three patch paths, confirmed the target files were unchanged locally, ran `git apply --check`, and applied once to the original workspace. Targets only: `templates/_risk_envelope_band.html.j2`, `templates/risk_envelope_live.js`, identical `site/risk_envelope_live.js`.

## What works and what was repaired

Existing native causes now survive recognized aggregate-null coverage/mapping gaps. Eligible partial warnings require a fresh, contributing, same-session source with a known warning state; aggregate stage remains UNKNOWN, not a confirmed whole-market finding. The existing risk button carries `Warning · partial read` / `警告 · 信息不全`. The actual settled bilingual hint is carried through the existing small copy JSON and restored after a live failure; no second envelope, private policy payload or new client storage exists.

Original worker patch passed the parent's11 focused partial/restore cases and8 offline real-Chromium functional cases. Parent review then found and reproduced6 additional failures: inherited JavaScript object properties accepted as native vocabulary, duplicate source warnings, and nonstring settled clocks. Parent repaired those checks. Three malformed-hint cases also failed and were repaired by requiring an exact two-string array. A wider test's closed-key expectation was updated from2to3 keys to reflect the deliberately added UI hint, while strengthening the assertion that no envelope/private policy data leaks.

These are parent repairs to the returned artifact, not an unchanged first-pass acceptance. Preserve original artifact hash alongside final source hashes. No changes to risk scores, calibrated forecast gates, source admission, numerical sizing, navigation, polling or application deployment.

## Verification

- `node --check templates/risk_envelope_live.js`: passed.
- `cmp templates/risk_envelope_live.js site/risk_envelope_live.js`: identical.
- `git diff --check`: passed.
- `pytest tests/test_risk_envelope_radar_integration.py --basetemp=/tmp/mmx-risk-response-ui-final-20261015 --tb=short`: **76 passed**.
- `verify_component_browser.py`: **8 passed** (dark/light × EN/ZH ×1440/390), actual headless Chrome, network blocked, source Jinja and JS used with synthetic source data. This proves offline component function, NOT production, full-app behavior or visual design quality.
- Previously completed and unchanged: chat/role-retention134passed/2existing xfailed; native envelope/live checkpoint182passed/2artifact-dependent skips;15/15 synthetic native-contract cases. Do not add these overlapping counts into a fabricated unique-test total.

## Disposition and remaining obligations

Accept the bounded frontend output after the recorded parent repairs and deterministic checks. Broader independent source integration review is a separate child `risk-response-integration-review-20261015-c1-01`, same root/parent, still pending at this write. No production/merge/release approval is implied. The current UI still needs the broader foreground warning hierarchy and existing#8132 publisher activation, data refresh qualification, held-out research, portfolio/setup consumers and production proof described in MISSION.md.
