# Private Press drafts from shared company news

This path adds fresh, audience-qualified news context to one existing ordinary Press slot. It produces a private editorial candidate and retains its complete evidence bundle. The existing Press publication owners remain responsible for any public article.

## Admission and source scope

Supply an original planned slot with the current UTC date and one explicit ticker. The canonical security universe must qualify at the actual read and provider-request times, and the ticker must resolve to one permanent security identity. The current-state news store is not a historical replay; a historical slot, stale universe, ambiguous alias or changed identity is refused.

The reader uses the existing qbus evidence adapter with the `blog_draft` audience and a limit of three story groups. Each supplied receipt must currently permit the projected fields and derivative processing. The retained private bundle records source item and revision identities, publication/receipt clocks, universe binding, receipt references and truncation. Existing receipts for another audience do not imply draft permission.

Publisher title and permitted description text are third-party evidence in the existing prompt evidence fence. They are not independent verification or first-party analytical value. The normal Press factual, originality, attribution and editorial-value validators still apply. Full article bodies and images are not introduced by this consumer.

Publisher links are admitted separately into prompt linking text: only HTTP(S) URLs with a host, no credentials, valid ports, and no raw whitespace, control/format characters or backslashes. An unsafe original remains only in the private evidence bundle; it is omitted from prompt links and fact URLs.

## One bounded attempt

The private entry point disables regeneration and provider fallback and uses the existing admitted token accounting with a maximum run budget of 12,000 tokens. The stricter existing configuration or environment limit still applies. The writer selects one currently usable provider and disables Anthropic SDK retries. Internal requests made by a Codex CLI adapter are outside the SDK request bound; this is not a new provider-spend grant.

Evidence is freshly prepared from the original slot. Permission and identity are checked again after the durable checkpoint, after provider construction and directly before the client request. A source-admission cancellation before any external request is recorded as a private refusal, with no provider usage charge or provider-failure classification. Any real provider request retains the existing failure and usage accounting.

## Operator invocation

Run only from a qualified, deployed source revision, using the existing admitted provider configuration. Keep the planned slot and output in an explicitly private directory outside the configured staging, content, site and publication trees. Use absolute paths. For example:

```sh
python3 scripts/run_press.py \
  --stage-qbus-news \
  --root /opt/macro \
  --qbus-slot /var/lib/macro-private-news-inputs/planned-slot.json \
  --qbus-db /var/lib/macro-ticker-news/qbus.sqlite3 \
  --qbus-universe /var/lib/macro-ticker-news/news_universe.json \
  --qbus-rights /etc/macro-ticker-news-massive-zacks-com-rights.json \
  --qbus-rights /etc/macro-ticker-news-massive-fool-com-rights.json \
  --qbus-rights /etc/macro-ticker-news-massive-globenewswire-com-rights.json \
  --qbus-staging-dir /var/lib/macro-private-news-drafts/current-candidate
```

Those receipt paths refer to the separately qualified publisher activation. The consumer never installs or expands a grant. It refuses when eligible evidence is absent or restricted. Do not manufacture a security identifier or change the slot date to evade a refusal.

The CLI returns zero only when that one candidate passes the existing validators. A provider refusal or validation failure remains a private checkpoint, with the exact reason and any returned draft retained for review. Retrying requires a new explicitly admitted operation, not an automatic fallback or regeneration.

## Publication boundary

Private candidates have their own `press-qbus-news-` identity and `qbus-news:` provenance markers. The generic `--emit` path refuses them before article, ledger or site publication, even when superficial approval flags have been removed and only a durable source/fact/document/slot marker remains. The private directory also resolves symlinks before rejecting overlap with any generic staging or served publication root.

Copying the candidate into generic staging does not grant publication authority. A future public release needs a separately qualified editorial and publication path; this integration supplies no automatic release or trading authority.

## Qualification

The companion tests use a real canonical news store, original and corrected revisions, actual prompt assembly and the real writer/provider-dispatch path with an isolated external client. They cover permission changes during checkpoint and provider construction, cancellation inside dispatch before the client request, URL prompt boundaries, current-date/security refusals, private directory containment, and generic-emitter refusal. Tests and live operation receipts distinguish provider calls from source-admission refusals.
