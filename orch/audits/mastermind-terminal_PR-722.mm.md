# Audit record — Terminal #722: Precision Entry selector contract

## Record status and source identity

This records-only reconciliation preserves the September23 library-contract audit and corrects its test and authority claims. Native metadata and both complete source postimages were inspected on 2026-11-06. Original Terminal #722 is already merged and remains DO_NOT_REDO.

- [Product PR #722](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/722), author chriswong6031-creator.
- Source head: `2680547e6d8f8c5fc8a2b2ceb0fcf2585d814c26`.
- Merge: `d4c71912ac9fc2168df9fe1da3f566327c8cc22d`, 2026-09-23T11:39:01Z.
- Native diff: two added files, +446/-0. Library229 lines, blob `0df70279f5e4270f9d9d0ed8c0913d33f556390d`; test217 lines, blob `ea813628b13e88c80eda2aa9dc3f0771058792e8`.
- [Original audit](https://github.com/mastermindx-market-intelligence/macro/blob/5d574d4e37cc1f588dfc08c5e20f0cdb46acc51a/orch/audits/mastermind-terminal_PR-722.mm.md), blob `9a6a6ae371f0324443c1dd4d1b6f7b0d8140cd0e`.

## Preserved contract

The library defines four explicit horizon recipes, in execution / trigger / durability / structure role order:

| Horizon | Recipe |
| --- | --- |
| Day | 5m / 15m / 1h / 4h |
| Swing | 4h / 2D / 3D / 2W |
| Position | D / 3D / W / 2W |
| Deep | 3D / W / 2W / 1M |

A normal3D chart infers Swing. Default substitution is deterministic, reserves later exact requested grains, avoids duplicate panes and limits fallback to two positions in the canonical ordering. An insufficient plan stays explicit and is not projected as a ready layout.

For typed accepted evidence, the selector checks subject identity and requires four unique canonical timeframes present in the functional set before using the exact recipe. Subject mismatch or a rejected recipe keeps the horizon default. Abstain and unproven remain non-adaptive states. The returned plan explicitly has `sync:false` and `replay:false`; layout projection uses the incumbent four-pane same-symbol state, and horizon detection reads an existing arrangement. The diff adds no shell consumer, chart renderer, CSS, HTML, asset, persistent mode or trading/sizing authority.

## Corrections to the original audit

- The test file contains **12 `it` definitions across two `describe` blocks**: nine selector cases and three layout cases, not nine tests in total. This is a source count, not12 observed executions.
- The accepted-evidence test fixture and its expectation contain the text `validated structural scale band`. Therefore a blanket claim that the diff contains no `validated` text is false. That test text is not newly rendered UI. The selector also passes an accepted input's reason through, so a future consumer must apply its own governed disclosure and copy rules.
- TypeScript's evidence union and `authority: "temporal-grain"` literal describe a typed caller contract. They do not authenticate an external evidence source or validate arbitrary untyped input at runtime. The inspected implementation checks subject and recipe; it does not establish a statistical, scientific or per-ticker optimal-timeframe validation result.
- Rejection, missing-grain and substitution paths can emit warning codes. Abstain and unproven are exposed through state/reason and need not each emit a warning. The original “every negative path emits a warning” statement is too broad.
- The inspected two-file source does not contain the alleged `setActive` fixture string or a Vitest lifecycle method of that name. No new claim is based on that passage.
- Library-only scope explains the absence of a new visible surface in this PR. It does not certify the copy, accessibility, browser behavior or production readiness of a future shell integration.

## Evidence and ownership boundaries

The original product body expressly declines a local Vitest pass claim because execution on its then-current worktree was starved; it names exact-head GitHub CI as the execution owner. This reconciliation does not invent or rerun that receipt. The audit's reported plain-language scan and six historical legacy findings remain attributed; they are not fresh whole-estate results.

The source preserves the original truth boundary: horizon presets are transparent defaults, and any accepted Temporal Grain input remains subject to its upstream authority and serveability constraints. It provides no new signal, rank, gate, size, trade, Prophet or Golden Oracle authority. The historical #606/#714 shell-custody disclosure explains why this slice remained in the library; it does not create a present named-seat approval requirement.

No product source, tests, layouts, market inputs or runtime state were changed by this record. A visible follow-up must use the existing shell owner and prove its actual consumer journey, with no new chart, layout or intelligence plane.
