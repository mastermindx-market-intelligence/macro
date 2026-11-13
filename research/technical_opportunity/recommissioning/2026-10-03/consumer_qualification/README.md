# Existing technical consumer — empty-source repair proposal

**Program:** WS:TECHNICAL-OPPORTUNITY-INTELLIGENCE. **Observed:** October 3, 2026 EDT / October 4 UTC.

**Disposition: tested isolated proposal, not an applied source repair or deployment.** This package advances the existing technical consumer's failure-path qualification while the TOI W1 source-custody, W2 data/release, S16 identity and W3 outcome gates remain held. It creates no opportunity detector, calibrated head, registry, data store, trade or consumer authority. The incumbent confluence screener is an existing descriptive product, not the completed TOI two-queue product.

## Observed failure and proposed behavior

At Macro `88804ed7079700c598bb8e04aa64307d1335402d`, the unchanged native `scripts/build_confluence_screener.py` clears public and premium rows when its source is missing, malformed, the wrong JSON shape, or empty. In all four synthetic reproductions, it leaves the prior `site/og/confluence_screener.png` file behind. The template also always points social metadata to that signal-specific image. Thus the generated empty page/payload can coexist with a stale signal card.

[The proposed three-path patch](EMPTY_SOURCE_REPAIR.patch) makes only these changes:

- Empty-source rendering removes its own previous share card with `unlink(missing_ok=True)`. Other images are untouched.
- An empty page leaves image/card selection to the existing shared SEO defaults: the neutral site image and `summary`. A nonempty page retains the existing screener-specific image and `summary_large_image`.
- Eight discriminating cases are appended to the existing `tests/test_confluence_screener_page.py`, retaining the incumbent test owner rather than introducing another suite.

Normal card generation, rank-one public preview, protected remaining rows, descriptive statistics and all access controls are unchanged. Image-generation failures for a nonempty source remain outside this narrowly tested repair; this package does not claim to fix every share-card failure. No real market source or statistical payload was acquired to produce these results.

## Exact source and proposal subjects

The source is the Macro revision returned by the restored Executive reader; it is not claimed to be the current production release or the newest default-branch revision. [Source receipt](SOURCE_RECEIPT.json) and [additional render dependencies](RENDER_DEPENDENCIES.json) retain exact Git blobs and SHA-256 values.

The patch applies to exactly three source paths: the incumbent builder, its template and its existing test file. It is published here as inert review evidence. Those actual repository paths and every production path remain unchanged by this documentation commit. `git apply --check` passes against the pinned original files; both Python files compile and the candidate template parses. Candidate hashes and the patch hash are in [repair proof](REPAIR_PROOF.json).

## Verification actually performed

| Subject | Result | Meaning |
|---|---|---|
| Unchanged native builder, four synthetic empty-source classes | Four stale-card reproductions | The old card survives while public/premium rows clear. |
| Eight new cases on original implementation | 5 failed / 3 passed | Four cleanup failures plus the empty-page SEO failure reproduce the defect. |
| Isolated repair proposal | 8 passed | Both intended fixes satisfy the new cases. |
| Remove only cleanup | 4 failed / 4 passed | Cleanup assertions discriminate the missing behavior. |
| Restore cleanup, remove only SEO condition | 1 failed / 7 passed | The metadata assertion discriminates the stale reference. |
| Restore complete proposal | 8 passed | Exact proposal restored before packaging. |
| First complete dedicated-file attempt in isolated cache | 31 passed / 2 failed | One committed-statistical-artifact file was absent; the native MinerConfig module was also initially absent. Neither failure was concealed. |
| Supply the unchanged native configuration module; exclude the real-artifact check explicitly | **32 passed / 1 deselected** | All source/synthetic cases in the dedicated file pass. This is not a full-repository or shipped-artifact pass. |

The excluded case is `test_shipped_shell_and_protected_payload_are_paired`. It reads the committed statistical HTML/payload. Those files were not acquired while outcome access is held, and no synthetic replacement was passed off as shipped evidence. [Initial scope limits](INITIAL_SUITE_SCOPE_LIMITS.json) preserve both original failures; [qualified suite receipt](QUALIFIED_SUITE_RECEIPT.json) records the final command, exclusion and result.

The new I/O cases execute the native `render`, `build_context` and `build_premium_payload` functions. They replace page writing with fixture-only I/O, HTML serialization with context serialization and share-card image generation with an inert synthetic image. Separate tests exercise the actual Jinja SEO fragment and the incumbent full-template tests. These seams do not prove real image rendering, real browser behavior, serving/cache invalidation, entitlement, or production deployment.

## Separate anonymous operating observation

[Header-only receipt](ANONYMOUS_PATH_HEADERS.json), observed at `2026-10-04T02:38:36.418761Z`:

- `/confluence_screener.html`: HEAD 200, HTML.
- `/premiumdata/confluence_screener.json`: HEAD 401, JSON, no-store.
- `/og/confluence_screener.png`: HEAD 401, JSON.

Requests used the canonical host from the repository SEO source, sent no credentials, read no bodies, and did not follow redirects. The protected responses were not retried with GET, another host or credentials. The 401 on the image means an anonymously fetchable social-preview path was not established by this observation. It does not prove what image bytes exist behind the gate, and the proposed empty-source repair does not alter or bypass that gate.

## Adoption and completion boundary

The active user authorized continued TOI work, but existing W1 custody was not released and the current source/custody compound read encountered an explicit platform refusal. That refused action was not replayed or routed around. The independent proposal cache is not a substitute source worktree, lease, accepted independent review or source-write admission. Executive read visibility recovered, but submission/autonomy/reciprocal-return flags remained disarmed; the separate Workbench manifest preflight returned `tunnel_client_not_seen`. No worker or watcher was launched.

The next source owner must acquire lawful current source custody, inspect the exact current three-path preimages and collisions, apply or recompose this minimal patch, run its own current-source tests including the real-artifact and required hosted checks, obtain independent acceptance, and verify the actual live user/share path. A changed current source requires a real delta review; do not overlay old blobs. Keep the public/premium access boundary unchanged and do not unlock outcomes merely to satisfy an unrelated artifact test.

This is a reusable implemented-and-tested **proposal**, not a claim that Mastermind is fixed live. TOI remains incomplete. The supplied research reconciliation, scientific/clock admission gates and original W1/W2 carriers continue to govern the parent mission.
