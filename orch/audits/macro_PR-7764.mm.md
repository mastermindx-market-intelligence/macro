# Audit record — Macro #7764: Markets stylesheet cache key

## Record status and provenance

This record preserves the useful September23 audit history and reconciles it against native source on 2026-11-06. It is a records-only assessment, with no new execution, cache purge, browser, deployment or served-page receipt. The original product repair is already merged and remains DO_NOT_REDO.

- [Original product PR #7764](https://github.com/mastermindx-market-intelligence/macro/pull/7764), authored by chriswong6031-creator.
- Source head: `22dcd95f40bc1ef40d53af762c60b00f0656f252`.
- Merge: `8316c3baa09dad0380825b607c15153f442206a2`, 2026-09-23T04:49:09Z.
- [Original audit](https://github.com/mastermindx-market-intelligence/macro/blob/5d574d4e37cc1f588dfc08c5e20f0cdb46acc51a/orch/audits/macro_PR-7764.mm.md), blob `84b2f36a3ec77cbaca7f8428f7156ea4cf72e687`. Its PASS statements and local-command output are historical reports, not current proof or an instruction to skip delivery.

## Source-supported change

Native GitHub reports exactly three changed files, +8/-3. Both `templates/markets.html.j2` and `site/markets.html` change the stylesheet URL from `markets.css?v=5` to `markets.css?v=6`. The existing test in `tests/test_markets_cyc_stage_mobile.py` finds the numeric stamp, requires it to be at least6, and retains the assertion that the Markets stylesheet follows `cycle.css` in the cascade. No stylesheet body, JavaScript, model, data registry, page copy or translation is changed by this PR.

The original author's incident report says the first request for the v5 key arrived before the origin's #7761 update. The edge consequently cached an old stylesheet body under that new key while the origin later held the corrected body. That is historical operational evidence attributed to the author; the audit does not independently measure the cache today.

## Cache-policy correction

The original audit's assertion that `markets.css` was absent from the immutable matcher is incorrect. The [Caddyfile at the exact source head](https://github.com/mastermindx-market-intelligence/macro/blob/22dcd95f40bc1ef40d53af762c60b00f0656f252/app/deploy/Caddyfile), blob `74fd839338b05a43a0302060e6ca37b1d40c65e6`, includes `/markets.css` in `@public_versioned`, matches `query v=*`, and sets `Cache-Control "public, max-age=31536000, immutable"`.

Changing the page's URL selects a different cache key; it does not purge the old key. The operational lesson remains useful: establish that the origin serves the intended bytes before requesting a new immutable asset key, then compare the page's selected stamp and the delivered asset bytes. An updated page timestamp alone cannot prove stylesheet identity or successful mobile interaction. The max-age value is not proof that every intermediary retained an object for exactly one year.

## Evidence boundaries

The product body reports30 local tests across the Markets mobile-stage and regime-strip suites. The historical audit separately reports23 hub plain-language tests with two warnings. Those are different historical scopes and are not combined into a new count or re-executed here. Its estate-wide scanner totals and design-system observations are likewise attributed to that audit's environment.

The three-file diff introduces no visible label or theme token. That narrow source observation does not establish a fresh dark/light, EN/ZH or responsive browser result, and it does not transfer #7761's screenshots to a newly served asset. Preserve the original product owner's acceptance path: observed page stamp, exact served stylesheet identity and the intended mobile cycle-stage interaction on the normal publication path. This record neither repeats that deployment nor creates a new publisher, cache controller or verification runner.
