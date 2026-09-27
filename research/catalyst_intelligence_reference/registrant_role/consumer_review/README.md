# Related-evidence consumer reference (R18)

This is an executable, source-local proposal for the already-owned Special Situations
consumer path. It is not a new service, collector, relationship registry, entitlement
checker, ranking model, or deployed correction.

## User outcome

A filing that mentions a take-private but does not establish that the registrant is the
target remains discoverable. It must not receive the target's arbitrage spread, sale
price, delisting semantics, or direct deal classification. Unknown relationship is not
silently asserted to be an indirect economic exposure either.

## Exact input and output

`project_relationship_review(records, *, as_of, limit=100)` consumes already-scoped
`build_situations()` records after the R15 guard. Only Going-Private/non-target rows
that have been deferred and cleared of direct fields qualify. The original unguarded
classification is explicitly refused. Other categories, explicit targets and skipped
records are not reclassified.

`attach_relationship_review(payload, records, *, as_of, limit=100)` produces a new
copy of the current snapshot or desk payload. It preserves the direct `situations`,
category counts and arbitrage inputs. It adds a derived source-review section and
separates relationship review from text classification in snapshot coverage. Reusing
an enriched payload, negative coverage or leaking withheld IDs into direct situations
is refused. Full source-record totals remain distinct from the bounded visible list.

No ticker-based deduplication is performed. Source-record IDs are not transaction IDs;
multiple disclosures do not establish independent investment evidence. Missing source
links and text stay missing. Unusable URLs remove the action, not the record.

## Rendering and access boundary

`render_fixture_fragment(..., entitled_fixture=..., locale=...)` exercises EN/ZH content,
autoescaping and source-link handling. The argument is a TEST FIXTURE, not an
entitlement or login API. It must never be wired directly to request parameters.

Production must render this view through the EXISTING authenticated/premium fragment
path and existing styles. No source name, symbol, text, URL or count belongs in a free
shell merely because the derived view exists. The supplied fragment is unstyled;
no complete-theme, mobile-browser, native Paper or visual-acceptance claim is made.

## Already executed engine boundary

M1 process 91339 imported the existing isolated R16 patched module, SHA256
`22e774a5633ec6b160d42db982119c23dae67e89a0a81557dcbd6a646fb23bb3`, with real
classification/lifecycle helpers and synthetic fixture I/O. It ran BOTH `snapshot()`
and `desk_payload()`. Digest/news/international inputs, price enrichment and premium
calculation were isolated. Only the direct record reached the arbitrage receiver.

`fixtures/ENGINE_TRACE_OBSERVED.json` is an explicitly labelled structured transcription
of that tool output, NOT a byte-verified copy of remote stdout and NOT live filing data.
The consumer tests run the new candidate against those observed engine outputs; they
do not rerun the remote module. R16's original-engine RED is preserved, not relabelled
as a new R18 test.

## Run

From this directory, with Python 3.11+ and existing pytest/Jinja2:

```sh
python -m pytest -q
python check_mutations.py
```

The committed suite includes 68 checks. Seven harmful variants must produce assertion
failures with zero test errors. The mutation runner writes `mutation_results.json`
locally. New artifacts from these commands are test output, never runtime state.

## Production integration still required

The existing engine owner must adopt or reimplement the candidate in its own module,
not import this research folder as another production kernel. Capture one native source
frame per publication; pass its compatible scope to both direct and review views.
The reference consumes caller-scoped records: it does not guess the application's
14-day window or historical-possession proof. Query/pagination/cutoff binding remains
with the incumbent provider/publisher and must be tested on the real build path.

Then connect the real paid renderer, per-ticker/Alt-Data projection and Catalyst reader,
with exact generation and entitlement parity. Related evidence must be context rather
than the old direct-target `special_situation` flag. Never infer a confirmed economic
relationship from a raw LLM role. Qualified transaction/relationship owners still need
to supply the real MGLD/USCF relation. Source-origin dedup, issuer-wide lifecycle, other
promotion routes and noise-filter losses are separate owed corrections.

This reference is not the full horizontal repair and not a live MGLD/USCF replay.
The original production module, #8087 specialist branch, frozen F07 and all live
ranking/trading gates remain untouched.
