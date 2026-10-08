# Low-Latency Ticker News R1 — Operator Activation

Status: **BUILT_NOT_PROVEN / DARK BY DEFAULT**.

This runbook activates the source/store side of the per-ticker News rail implemented
by Macro PR #8454 and Terminal PR #831. It does not grant source rights, buy a feed,
or authorize a production release. Source rights, provider credentials, merge/release,
and production acceptance remain separate gates.

## Ownership

| Concern | Existing owner |
| --- | --- |
| Provider observations / revisions / history | qbus |
| S&P 500 membership | breadth constituent + PIT membership datasets |
| Security identity / aliases | Data OS security master + vendor aliases |
| Source rights | source-rights / contract owner |
| Runtime process | systemd on the Macro API VPS |
| API auth / product entitlement | existing Macro API / Terminal auth owners |
| Browser presentation | Mastermind Terminal |
| GMI related-subtheme context | GMI, deferred from R1 direct-news activation |

There is exactly one live news writer. `macro-api` receives read-only access to the
qbus hot store and the qualified rights receipt; it never receives the provider key.

## Required commercial-rights evidence

Do not create an `approved` receipt from API possession alone. The contract/order or
other current source-rights owner must positively establish the uses below.

The current R1 architecture requires these capabilities to be **true**:

- `internal_ingestion`
- `historical_retention`
- `headline_display`

These remain separately explicit and default-deny when missing:

- `source_link_display`
- `teaser_display`
- `body_display`
- `image_display`
- `derivative_processing`

R1 does not display provider body text or images. Later LLM enrichment must not be
enabled merely because R1 headline display is licensed; derivative/model processing
has its own receipt field and later acceptance.

If historical retention is not licensed, **do not arm this service**. Redesign the
persistence policy first rather than weakening the receipt gate.

## Root-only activation files

Two operator-owned files are required on the Macro API VPS.

### `/etc/macro-ticker-news.env`

Mode: `0600`, owner: root, exactly one provider-token line:

    BENZINGA_API_KEY=<licensed commercial newsfeed token>

Do not put this key in `/etc/macro-api.env`. The API unit explicitly hides this file.

### `/etc/macro-ticker-news-rights.json`

Mode: `0600`, owner: root. Template:

    {
      "schema": "qbus.news_rights_receipt.v1",
      "receipt_id": "<unique owner receipt id>",
      "owner_ref": "<contract / order / approved-rights evidence ref>",
      "status": "approved",
      "source": "benzinga",
      "product_id": "<exact licensed Benzinga product/account>",
      "audiences": ["site_full"],
      "effective_at": "2026-10-06T00:00:00+00:00",
      "expires_at": "<actual rights expiry or review boundary>",
      "capabilities": {
        "internal_ingestion": true,
        "historical_retention": true,
        "headline_display": true,
        "source_link_display": true,
        "teaser_display": false,
        "body_display": false,
        "image_display": false,
        "derivative_processing": false
      }
    }

Use the contract's actual scope. Do not copy the booleans above as an assertion of
rights. Missing, malformed, future, expired, wrong-source, wrong-audience, or denied
receipts fail closed.

The receipt is re-read continuously by the writer and on every API access. Revoking,
expiring, or replacing it with a non-qualified receipt stops new ingestion and
withholds display without changing source code.

## Network-dark preflight

From the production VPS, after the merged/released source is present at `/opt/macro`:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --check

This action:

1. serializes with the existing `macro-update` lock;
2. requires root-owned `0400` or `0600` activation files;
3. verifies the production Python runtime includes the synchronous WebSocket client;
4. rebuilds the exact current S&P universe from the incumbent breadth + Data OS owners;
5. verifies the provider token is present;
6. validates current site-full source rights;
7. validates the universe is current and complete;
8. opens **no provider connection**;
9. creates **no live database** and **no health claim**.

A passing check is activation readiness, not production proof.

## Install disabled

After the network-dark check passes:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --install

This installs the reviewed `macro-ticker-news.service` and reloads systemd, but does
not enable or start it. If a writer is already active, install refuses; disarm first
rather than hot-swapping the unit under a live process.

Routine `macro-update` deployments never install or enable an absent ticker-news
service. Once an operator has installed it, the updater may reconcile the reviewed
unit and restart an **already-active** writer when import-cached code or canonical
universe inputs change.

## Explicit arm

Only after rights, source code, runtime, and release approval are all current:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --arm

`--arm` performs the same activation check and reviewed-unit install, then explicitly
runs `systemctl enable --now macro-ticker-news.service`.

Startup activation refusals use exit code 2 and are in
`RestartPreventExitStatus=2`, so missing/expired rights or other operator
prerequisites cannot cause a five-second restart storm. Transport/runtime failures
may restart. A mid-run rights revocation exits cleanly and remains stopped.

## Status and logs

Status is observational:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --status
    sudo systemctl status macro-ticker-news.service --no-pager
    sudo journalctl -u macro-ticker-news.service -n 100 --no-pager

Runtime state lives in the private systemd state directory:

- `/var/lib/macro-ticker-news/qbus.sqlite3`
- `/var/lib/macro-ticker-news/news_universe.json`
- `/var/lib/macro-ticker-news/health.json`

The API has read-only access to that state and to the rights receipt. It has no access
to `/etc/macro-ticker-news.env`.

## Canary acceptance

A canary is not production acceptance. At minimum capture:

1. exact Macro + Terminal release SHAs;
2. service `MainPID`, active state, and current health receipt;
3. exact universe revision and count;
4. authenticated Terminal snapshot for a covered ticker;
5. one synthetic/controlled correction path;
6. one controlled removal path;
7. restart + REST catch-up proof;
8. rights downgrade proof;
9. browser News rail proof;
10. rollback proof.

Never paste provider payload bodies or credentials into GitHub evidence. Metadata,
IDs, clocks, counts, digests, and redacted headlines are sufficient.

## Natural proof

Final R1 acceptance still requires the plan's natural-market evidence: at least five
actual trading sessions, including an event/earnings burst, with measured source
quality, duplicate escape rate, ticker-routing precision, correction/removal
behavior, source/publication-to-receipt clocks where trustworthy, and truthful
freshness during an upstream interruption.

Synthetic load evidence proves implementation capacity only.

## Rollback / disarm

Immediate source stop:

    sudo /opt/macro/app/deploy/ticker-news-setup.sh --disarm

Then verify:

    systemctl is-active macro-ticker-news.service
    systemctl is-enabled macro-ticker-news.service

Both must report inactive/disabled semantics before considering the writer stopped.

Do not delete the qbus store as part of ordinary rollback. Preserve it under the
applicable source-rights retention/deletion policy so corrections, removals, and
audit evidence are not silently lost.

## Current external gate

At source publication time, the local development environment had no repo-level
secret names for Benzinga/Massive/Polygon/ticker-news rights. Organization-level
secret presence could not be inspected with the current GitHub credential and
remains **unknown**. The source therefore makes no claim that a production credential
or commercial display right already exists.
