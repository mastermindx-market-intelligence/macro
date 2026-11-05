---
key: VPS-ALPACA-CREDENTIALS-SILENTLY-REJECTED-SINCE-2026-08-04
claim: >
  Every VPS consumer of the Alpaca Market Data key pair (marketing-press-feeds.service via
  /etc/macro-live.env; the macro-ticker-news writer via /etc/macro-ticker-news.env) has been
  answered HTTP 401 since 2026-08-04: the pair was rotated that day (repository secrets
  ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY updated 05:22Z, and the GitHub-hosted
  marketing-press-wire.yml lane keeps working on them) while both VPS env files kept the
  pre-rotation pair, and nothing alarmed — the press lane's cursor froze at
  2026-08-04T04:04:42Z, the unit stayed active (Restart=on-failure never fires on a 401
  loop), and no health surface distinguishes "401 for two months" from "no news".
falsifier: >
  A journald line from marketing-press-feeds.service between 2026-08-04T05:30Z and
  2026-10-11 showing an Alpaca 2xx, a press cursor on the VPS advancing past 2026-08-04, or
  a 2xx from the ticker-news writer under the unrefreshed VPS pair.
so_what: >
  (1) A credential rotation in GitHub Secrets does not reach the VPS by itself — every VPS
  env copy needs a delivery act (now .github/workflows/deploy-alpaca-secrets.yml,
  DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW); a lane that
  "works in Actions" proves nothing about the VPS copy, and a file mtime newer than the
  rotation is not evidence the pair is current. (2) VPS Alpaca consumers must surface auth
  failures as a distinct health state (ticker-news health.json error code, a press-lane 401
  counter): a fail-closed loop that logs 401 once a minute for two months is
  indistinguishable from a quiet feed on every dashboard the estate owns.
kind: runtime
verified_at: 2026-10-11
verified_by: >
  seat fd47d431 — journalctl -u marketing-press-feeds --since -2h | grep -c "HTTP 401" = 88;
  /opt/macro/data/marketing/press/state.json since=2026-08-04T04:04:42+00:00 (earliest
  surviving journal 401 line 2026-10-08T23:10Z, journal rotated); gh api
  repos/mastermindx-market-intelligence/macro/actions/secrets updated_at 2026-08-04T05:22:16Z
  / 05:22:24Z; env presence and shape checks only (one line per key in each file, len 26/44,
  identical in both, values never read); marketing-press-wire.yml run 38151897625 fetched
  50/50 on the repository secrets at 15:35Z; ORCH-N packet 17:04Z (dummy-key probe 401,
  writer armed under the VPS pair fails closed with 0 rows, no real-secret probe)
scope: macro/marketing/app/deploy/marketing-press-feeds.service/app/deploy/ticker-news-setup.sh/.github/workflows/marketing-press-wire.yml//etc/macro-live.env//etc/macro-ticker-news.env
confidence: verified
---

Found while ORCH-N armed the Package N writer (2026-10-11 16:55–17:04Z): the adapter's
dummy-key probe returned 401 as expected and the writer under the VPS pair also failed
closed with 0 rows, so the seat traced the pair itself. The journal is rotated (earliest
surviving 401 line 2026-10-08T23:10Z), so the first-failure instant is bounded by the cursor
freeze (04:04Z) and the secret rotation (05:22Z), not observed directly. /etc/macro-live.env
carries an mtime of 2026-08-29 — later than the rotation — yet its pair is rejected, which is
why a rewrite of the file is not evidence that the Alpaca lines were refreshed. Repair =
DEC:VPS-ALPACA-PAIR-REFRESHED-FROM-REPO-SECRETS-BY-DISPATCH-WORKFLOW; the alarm gap (so_what
2) is owned by the press lane and the ticker-news health surface, not by that decision.
