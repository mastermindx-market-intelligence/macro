---
key: VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW
question: >
  Package N's P2 (ticker-news writer live on the VPS) blocked on HTTP 401 from Alpaca: the
  VPS copy of ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY in /etc/macro-live.env and
  /etc/macro-ticker-news.env is the pre-rotation pair (repository secrets of the same names
  were rotated 2026-08-04T05:22Z and still work in marketing-press-wire.yml), no
  human-readable copy of the current pair exists anywhere the seat may read, and the
  Chairman's 2026-10-11 directive assigns the seat to clear administrative blockers itself.
  How is the VPS copy refreshed lawfully?
answer: >
  By a dispatch-only GitHub Actions workflow, .github/workflows/deploy-alpaca-secrets.yml,
  modeled on the repository's existing secret-delivery idiom (deploy-api-secrets.yml,
  deploy-analytics.yml): it reads the two repository secrets into step env, delivers them
  over SSH (VPS_DEPLOY_KEY, materialized 0600 for the job only) via stdin, backs up each
  target env file (0600, timestamped), replaces exactly the two ALPACA_* lines in
  /etc/macro-live.env and /etc/macro-ticker-news.env, and prints line COUNTS only. It
  restarts nothing by default: the ticker-news writer is re-armed by its own setup script
  (--disarm/--arm, it reads env only at start) and marketing-press-feeds is restarted only
  on an explicit input. No credential value enters a transcript, log, record, packet or
  argv.
rationale: >
  The VPS is the credential's designated production holder — both files already held the
  pair, and the Alpaca rights basis (DEC:TICKER-NEWS-ALPACA-BENZINGA-RIGHTS-BASIS) rests on
  that pair being usable there. Refreshing a stale copy on its existing holder through the
  repository's own sanctioned GitHub-to-VPS secret path is a deployment act, not a credential
  transfer to a new account, agent or device, and it is the only path that never exposes the
  value to a model. The press-feeds daemon has been dead on 401 since 2026-08-04
  (DSC:VPS-ALPACA-CREDENTIALS-SILENTLY-REJECTED-SINCE-2026-08-04), so the refresh also
  repairs an unnoticed two-month outage. Reversible: each backup is restored with one mv.
alternatives:
  - option: Hand the Chairman the exact human action (paste the current pair into both files)
    why_not: >
      Contradicts the 2026-10-11 directive to self-remedy administrative blockers; the
      current pair is held nowhere human-readable except the Alpaca dashboard, so this would
      force a second rotation; and the repository already owns a lawful machine path for
      exactly this delivery.
  - option: Read the secret on a runner or on the seat host and write it to the VPS by hand
    why_not: >
      Forbidden — a value would enter a transcript or log; the saved-credential permission
      forbids printing, exporting or replicating credentials.
  - option: Extend deploy-api-secrets.yml with the Alpaca lines
    why_not: >
      It targets /etc/macro-api.env and /etc/macro-admin.env and restarts macro-api and
      admin; the Alpaca consumers read other files and unrelated production units must not
      restart for this.
  - option: Leave P2 blocked until a human places the pair
    why_not: >
      Package N stays dark indefinitely and the press lane stays dead; the blocker is
      administrative, not a consent, money or security boundary.
evidence:
  - "VPS: /etc/macro-live.env (mtime 2026-08-29T03:56:42Z) and /etc/macro-ticker-news.env (2026-10-11T14:00:23Z) each hold one ALPACA_API_KEY_ID line (len 26) and one ALPACA_API_SECRET_KEY line (len 44), identical in both; presence/shape only, values never read — seat 2026-10-11 17:1xZ"
  - "VPS journal marketing-press-feeds.service: 88 HTTP 401 lines in the trailing 2 h; /opt/macro/data/marketing/press/state.json since=2026-08-04T04:04:42+00:00"
  - "gh api repos/mastermindx-market-intelligence/macro/actions/secrets: ALPACA_API_KEY_ID updated_at 2026-08-04T05:22:16Z, ALPACA_API_SECRET_KEY 2026-08-04T05:22:24Z, VPS_DEPLOY_KEY present (2026-07-05)"
  - ".github/workflows/marketing-press-wire.yml L178-179 consumes the same two secrets; run 38151897625 (2026-10-11 15:35Z) fetched 50/50"
  - "No saved Alpaca pair on the seat host: no ALPACA_* env, keychain lookup rc=44, ~/.config/mastermind/credentials holds no Alpaca entry (presence checks only)"
  - "ORCH-N packet 2026-10-11 17:04Z: dummy-key probe 401 (code path reaches Alpaca auth); writer armed under the VPS pair fails closed with 0 rows; no real-secret probe by the orchestrator"
  - "app/deploy/ticker-news-setup.sh L61-71: the env file must hold exactly one non-empty CR-free line per ALPACA_* key — the workflow's strip-then-append preserves that contract"
affects:
  - WS:MARKET-INTELLIGENCE-INSTITUTIONAL-BUILDOUT
  - .github/workflows/deploy-alpaca-secrets.yml
  - app/deploy/ticker-news-setup.sh
  - app/deploy/marketing-press-feeds.service
  - docs/ops/ticker-news.md
confidence: high
reversibility: easy
decided_by: coo-fable (seat fd47d431, Chairman 2026-10-11 autonomy directive)
decided_at: 2026-10-11
review_by: 2027-04-11
---

The workflow is the only sanctioned writer of the VPS Alpaca pair from now on: a later
rotation is "update the two repository secrets, dispatch deploy-alpaca-secrets.yml, re-arm
the writer". A workflow_dispatch resolves against the default branch (a dispatch from the PR branch answered
404), so the first refresh waits on #8838's merge; the backups it leaves (`<file>.bak-alpaca-<ts>`) are the rollback.
The VPS Alpaca consumers still do not alarm on 401 — that gap is the DSC's so_what, owned by
the press lane and the ticker-news health surface, not by this decision.
