# Independent private-consumer source review

**Verdict: APPROVE source. Final test binding complete. Capability: BUILT_NOT_PROVEN. Parent mission remains incomplete.**

Reviewer: `/root/news_delivery_ruling`; author: `/root/news_consumer_admission`; parent owner: `/root`.
Repository: `mastermindx-market-intelligence/macro`. Base: `c73fa2c3d08e777221fe1ee73f3b87dd479f1fb8`.
This is independent source evidence for the parent's Git carrier. Managed tests, CI, deployment, and runtime proof retain their separate owners.

## Exact binding

| Product file | SHA-256 |
|---|---|
| `engine/press/qbus_news.py` | `b4e75e83697ec4b629313dfd593830fc41040326c3da2e9b4c168dc684540947` |
| `engine/press/writer.py` | `895fea2a5f135562bf8e61d3393eca1cb0e665c77808d44937eafd0ddd648be6` |
| `scripts/run_press.py` | `46e7761acbfb0f8cd8fe10c8ac51f18d196a651a0ccc023b8dcf77a1208171d2` |

Final reviewed `tests/test_press_run.py`: `5827148fc6e899c191a5a8dca562103f3df909498eb749e164dba1c1ae367cc3`.

Apply the reviewed patch chain in order:

1. `private-qbus-news-draft.patch` — `10512e8096a4cd1c183037aeb0cd432ad6ff4984a5b87756a9d242d903fe3a15`
2. `private-qbus-news-draft-after10512.patch` — `79b927e2c524dddd00943b558e4dce5a30ca52395d2cfeb08325596912643f8c`
3. `private-qbus-news-draft-after79b.patch` — `2c9de3eb45ddb28087865269aa9fafa0472a3016587167e93d9f84e77378acff`
4. `private-qbus-news-draft-after2c9.patch` — `0f147fe6833b961e9a6cd9389047820affec26e69852baaf1805660e88c36278`

The untransferred third-delta hash `8b92f5961bad05dbbb23d50eb71633b998233201b42ef2fa338c5cebcd1b117d` was superseded by `2c9de3…`. The final `0f147f…` delta changes only the test's usage-record assertions. All three product hashes remain unchanged.

## Rulings

- **URL trust repaired:** only strict HTTP(S) source projections enter fact URLs and trusted linking text. Rejected raw URLs remain private provenance. The canonical-store regression inspects the actual writer prompt.
- **Actual-request admission repaired:** fresh private checks follow provider construction and immediately precede `messages.create`. The private `BaseException` sentinel bypasses the real adapter's provider-error catcher and is explicitly caught by the writer. Actual client exceptions retain normal accounting.
- **Malformed identity repaired:** original collection validation precedes held-rail probes. The detector handles scalars and preserves standalone and dictionary-key private markers.
- **Defaults preserved:** hooks remain opt-in. The private rail uses one usable provider, admitted tokens, and zero regeneration. Preparation starts from the original slot. Helper retry coverage does not broaden that contract.
- **SQLite fixture correction accepted:** only the exact DB's `-wal`/`-shm` paths are excepted; private output remains required and complete `mode=ro` logical dumps must match.
- **Usage-record correction verified:** terminal success already stores usage/cap in `attempts[0]`. The final test asserts one successful attempt, reported positive usage and equality with `writer_state.tokens_used`. No serializer/product change was needed.

The earlier retained-draft/evidence mismatch remains outside the zero-regeneration private path.

## Independent evidence

Exact candidate writer plus canonical `c73fa2…` `make_call` passed eight isolated denial cases: zero requests, Press accounting, provider-health/usage records, pool effects, or dead-provider changes. Six default/admitted provider-error cases matched the base; unrelated interruption exceptions retain their existing propagation. Prompt/model/provider construction and telemetry sinks were isolated; no live provider was called.

Four outer/nested dictionary-marker probes and five malformed-scalar probes passed. Final test source retains real writer and adapter handling, including a fake-client transport failure. The final per-attempt-usage diff and all listed file/patch hashes were independently checked. The success fixture uses a 1,200-token output budget and supported synthetic first-party facts; validator thresholds remain unchanged.

## Parent-owned qualification and remaining gates

Parent reports the final managed four-suite run **passed: 252 tests, one existing skip**, completed **2026-10-20 17:24:35 UTC**, with no live provider call. This reviewer did not independently execute that repository run.

Parent also reports successful canonical CI closure derivation; the resulting manifest-only delta is a separate pending bounded review. Actual CI/release acceptance, live private placement, canonical inputs, licensed rights, and real private-provider proof remain parent-owned. Primary PR9846's merge as `1298ed4281362329c682a1f7c038b932e4ccbb64` is parent-reported and does not establish private-consumer runtime acceptance.

## Continuation

Parent commits this receipt with the final source, binds final-carrier CI, and qualifies the live private-consumer path under existing permissions. The manifest-only review can proceed when its exact diff is supplied.

Protected procedure compatibility was verified at Mastermind `b96dd69efb0588c3a678ee09ddd5408fa5a40b12`, skillpack `1.0.1` / bootstrap major `1`. This local evidence becomes durable when committed by the parent. Updated 2026-10-20T17:29:47Z.

