# Copilot market question failure — source diagnosis, 17 October 2026

**Live usefulness failed; a bounded source counterexample is complete. No production repair is claimed.** The unchanged captured response is in [the backend record](../runtime_response_record.json). The signed-in default-Fast user request completed with only a portfolio caveat after approximately 175 seconds.

## Evidence chain and limits

The exact question asked about technology rotation versus broader risk-off, protection, spreading danger, re-entry, source dates and the meaning of the 21-day 22% number. Its final constraint was “No portfolio percentages or trades.” The actual pinned classifier routes that question to `portfolio_current` solely because that constraint contains `portfolio`, requiring `get_portfolio_brief` or `get_watchlist`. Removing the constraint or replacing it with “No numerical allocations or trades.” yields the ambiguous general question profile. Affirmative private-portfolio questions still correctly require portfolio evidence in the controls.

The pinned gateway has a second defect: when synthesis is blank, the evidence-repair flag is false and adverse coverage exists, its finalizer appends a caveat. That nonempty caveat bypasses a later empty-answer check. In the five-case finalization suite and six classifier controls, the blank-without-repair case and composed classifier-to-finalizer case reproduce the exact observed caveat; the other cases are controls and supported prose is preserved. A synthetic macro-scoped contradiction also contaminates the portfolio coverage family because the reader-level mapping ignores scope.

The live response record and contemporaneous journal bind blank synthesis and the reported flags (`degraded:false`, `error:false`). They do not identify the provider stop reason or prove the actual repair flag and contradiction payload. The source examples establish mechanisms and a counterexample, not a full provider replay or a single proven cause for the model returning no prose. Token counts are metering, not causal evidence.

## Reproducibility

[The diagnostic](reproduce_finalization.py) reads exact Git objects at `15bdaec7351dbe2f1bf1a227b6e7498a8b3c0ac7`, verifies both SHA256 values, and executes only selected original AST nodes. It imports no first-party module and calls no provider. If those retained objects are unavailable, it refuses; it does not fetch another revision or substitute source.

From an existing Macro checkout that contains the pinned objects:

```sh
python3 research/grey_deer/live_delivery_20261017/copilot_failure_trace/reproduce_finalization.py --output /tmp/risk-radar-finalization-reproduced.json
```

An optional `--source-root` accepts an already captured exact tree. `--record` selects the captured request. Output is written only to an explicitly supplied path; the committed counterexample is not the default output destination.

The source reader/output-path adaptation was checked once against the originally reviewed extraction. All five finalization and six classifier controls pass; [the result](finalization_counterexample.json) is byte-identical to the original, SHA256 `61c23927d97dbf0eae5cfe006780db01f9dd2111893d9fcff5eeb8ec7ee58151`. The original [review](FINDINGS_2026-10-17.md) remains unchanged. Its script hash names that original extraction; the successor diagnostic changes only how source and artifact paths are resolved.

## Concrete repair contract

1. Distinguish a prohibition on portfolio actions from an affirmative request for private portfolio analysis. Preserve mandatory private evidence for genuine holding/account questions, including when those questions also prohibit percentages or trades.
2. Preserve a supported general market answer when a separate private-data family is missing. A caveat alone must not count as successful synthesis. Every empty/unsupported synthesis path must produce an honest failure state and a useful scoped fallback where available.
3. Attribute contradiction evidence by actual scope and question family; a global contradiction reader hit is not automatically a portfolio contradiction. Retain real contradictions and unavailable evidence explicitly.
4. Require source-level counterexamples, canonical authorization/visibility tests, the installed changed path, and one useful authenticated answer to the original market question. Check question scope, evidence dates, withheld forecasts, probability meaning and lack of numerical-policy overreach. Tests or source merge alone do not accept the user job.

The actual gateway writer #9447 retains its open draft and pending integration. This evidence carrier does not modify that source path or treat an old commit time as proof that writer custody expired. The diagnostic is a bounded regression witness for a custody-qualified repair, not a second gateway or provider route.

## October18 portable-reader verification

The adopted diagnostic was executed once on the owned M2 successor using `--repository` and the exact existing Git objects, with output confined to `/tmp/risk-radar-copilot-git-reader-20261018.json`. It exited0 and produced the same10,691 bytes as `finalization_counterexample.json`, SHA256 `61c23927d97dbf0eae5cfe006780db01f9dd2111893d9fcff5eeb8ec7ee58151`. The five finalization cases and six classifier controls retain their original outcomes. This verifies the portable source reader; no live provider or product request was rerun.
