# BioCatalyst PR #6389 maintenance evidence — 2026-09-17

Source head captured: `7b3e19c4bae32ed296cd6d0631a52d97fef00390`.

This package is release-maintenance evidence for the historical-event radius fallback repair. It is not production acceptance, an authenticated paid-session capture, or permission to merge/publish/deploy.

## Verified

- Canonical radius fallback regression: 6/6 passed after an observed 6/6 RED on inherited bare `var(--r-*)` rules.
- Historical-event UI suite: 12 passed on the integrated source.
- Broad `tests/test_biocatalyst*.py` suite under the retained Python 3.12 environment: 1,408 passed, 10 warnings.
- Headless Chromium computed-style discriminator on dark and light: absent global tokens compute panel/control/card/pill fallbacks as 14/8/12/999px; injected 31/32/33/34px root tokens override them exactly. Scratch receipt SHA256: `ac03081beccbd9d9050a40f2fbed4dce81978d2b9e40632e783708612ed33fb9`.
- Static eight-state capture: desktop/mobile × dark/light × EN/ZH, 8/8 captured, zero horizontal overflow. Manifest SHA256: `c4d3dcfcf415db66abdd3eb97c3baf7eb6e3541d0fa7aa64a5c6ef9bf1244298`. Smell report SHA256: `632d5d5d2f5921068f05f2ac28a2034cdf78bd6b5f7a6b059ff460f8ac6d3b0f`.

## Limits

The eight-state capture serves generated `site/` bytes from a local static server. The historical-events and catalyst-radar API requests therefore return expected static-server 404s; those failures are retained in `manifest.json` and are not relabelled as authenticated product proof. This package does not prove production entitlement, live API data, deployment, release readiness, H1/H2/H3 semantics, or current-main state after the named source head.
