# Render-lane outage 2026-09-23 → 2026-09-25 — the queued-job hostage, again

**Status:** root cause proven; detection hole closed in this PR; **capacity restore is
operator-owned and still open.**
**Lanes down:** `render.yml`, `engine-render.yml`, `sector-intelligence.yml` (and
`codex-research.yml`, independently, on the same mechanism).
**Blast radius:** 1,479 committed `site/**.html` pages carry the pre-#7970 nav. See the CORRECTION in §"Why the site went stale anyway" — the proximate cause is a PARTIAL 2026-09-25 nightly, not the render lane's estate; the outage explains why the split persists.
**Prior art:** `research/PROPHET_OUTAGE_2026_08_17_POSTMORTEM.md` —
`DSC:QUEUED-JOB-HOSTAGE-HOLDS-THE-NIGHTLY-CRON-GROUP`. Same mechanism, five weeks later,
reached through a door the fix for the first one did not cover.

## 1. What was NOT the cause

The reported hypothesis was a concurrency livelock: `cancel-in-progress: true` on a lane
that main pushes to every few minutes, so each push kills the in-flight bake. **Falsified.**
Both lanes already carry `cancel-in-progress: false`:

| file | group | cancel-in-progress |
|---|---|---|
| `.github/workflows/render.yml:245` | `pipeline-render` | `false` |
| `.github/workflows/engine-render.yml:73` | `pipeline-engine-render` | `false` |

Set by the 2026-07-17 starvation postmortem, whose in-file comment records the exact
symptom the hypothesis described (`true` "cancelled 27 of 30 renders").

The ~25 `cancelled` runs are **superseded pending runs, not killed work**:

* every cancelled run has an **empty `startedAt` and empty `runner_name`** — it was never
  assigned to a runner, so there was nothing in flight to cancel;
* each cancelled run's `updatedAt` equals the **next** run's `createdAt`, to the second —
  the supersede instant.

That is GitHub's supersede-of-*pending* behaviour, which `render.yml`'s own concurrency
comment relies on as its coverage mechanism (the `pick` step's per-region scope-union
watermarks re-render whatever a superseded run would have covered). **The lane was
working as designed. It simply had nowhere to run.**

## 2. What the cause was

**Zero online runners carry the `render-linux` label.** Live pool, measured 2026-09-25:

```
org   15  pc-render-1   online  idle  self-hosted,Linux,X64          <- render-linux GONE
org   12  pc-ci-1       online  idle  self-hosted,Linux,X64,ci-linux-canary,ci-linux
org   13  pc-ci-2       online  idle  self-hosted,Linux,X64,ci-linux
org   14  pc-ci-3       online  idle  self-hosted,Linux,X64,ci-linux
org   20  pc-ci-4       online  idle  self-hosted,Linux,X64
org 16/17/18 m1-*       online  idle  (m1-nightly-2 carries m1-theta)
repo 28/29/30/35 mac-builder-*         macstudio, macstudio-light, render-heavy,
                                       merge-control, theta-m1, parked
```

`render-linux` is the **only** label referenced by any workflow with no carrier anywhere.
`pc-render-1` keeps org runner id **15** — a low, original id — so the host was never
re-registered; its custom labels were **stripped** down to `{self-hosted, Linux, X64}`,
which is exactly the read-only set that
`DELETE /orgs/{org}/actions/runners/{id}/labels` leaves behind.

### Exact chain, at job level

| run | job state | evidence |
|---|---|---|
| `35676379868` | **success** | job started `2026-09-22T05:11:10Z` on `pc-render-1`, labels `self-hosted\|render-linux`, done `07:43:32Z` |
| `35819881039` | **failure** | job started `2026-09-23T09:45:34Z` on `pc-render-1`, done `12:05:08Z`. Failed at step 19, *"guard — stock dossier integrity (sentinel + identity)"* — a **real guard red on a healthy runner, not infra**. The last job ever assigned. |
| `35855143666` | cancelled | job created `2026-09-23T12:05:09Z` (1s after the above released the host), `runner_name` **empty**, completed `2026-09-24T12:05:09Z` = **+24h00m00s exactly** → GitHub's self-hosted queued-job kill. Never assigned. |
| `35989213316` | **queued** | job `107623716720` created `2026-09-24T12:05:10Z` (1s after that kill), labels `[self-hosted, render-linux]`, no runner. Still queued >20h; own kill due `2026-09-25T12:05:10Z`. |
| `36095283218` | pending | the rolling single pending run |
| ~25 others | cancelled | superseded as pending, `startedAt` empty |

So capacity was lost inside **`2026-09-23T12:05:04Z` → `12:05:09Z`** — five seconds after
the last job released the runner.

### Why the site went stale anyway, and by how much

`daily.yml` is unaffected (it routes `[self-hosted, macstudio]`, a live label) and so are
`closing-bell` / `asia-close`. That is why the site kept getting a partial nightly bake and
the outage looked like nothing: the nav entry PR #7970 merged at `04:38Z` did reach most
pages via `969883bc973 engine: regime update 2026-09-25` at `07:52Z`. Probing with the
`am_edition.html` nav entry that #7970 added — pages carrying `<nav class="site-nav">` but
lacking the entry:

| area | stale pages |
|---|---|
| `site/stocks/` (ticker dossiers) | 1,251 |
| top-level `site/*.html` | 111 |
| `site/sectors/` | 41 |
| `site/basket_china,_intl,_hk,_canada/` | 72 |
| `site/basket/` | 4 |
| **total** | **1,479** |

**CORRECTION — this table is NOT the render lane's blast radius.** An earlier revision of
this section claimed the 1,479 pages are "the estate the render lane's scope-union owns",
i.e. pages the nightly cannot reach. That attribution is false, and the arithmetic falsifies
it exactly:

| commit | lane | `site/stocks/` files rewritten |
|---|---|---|
| `fab3ad33b72` nightly 2026-09-24 | `daily.yml` (live `macstudio`) | 2,687 of 2,736 |
| `969883bc973` nightly 2026-09-25 | `daily.yml` (live `macstudio`) | **1,485** of 2,736 |

`2736 - 1485 = 1251`, which is exactly the stale `site/stocks/` count in the table above —
not approximately, exactly. And the 09-24 nightly rewrote 2,687 of those same pages, so they
are unambiguously **inside** the nightly's estate, not the render lane's. Three sampled stale
dossiers (`ABAT`, `ABEO`, `ABOS`) last baked at `fab3ad33b72` (2026-09-24T09:39Z) while
`A`/`AA` baked at `969883bc973` (2026-09-25T07:52Z).

So the proximate cause of the nav split is that the **2026-09-25 nightly delivered a partial
site bake** — 1,485 stocks pages where the night before did 2,687 — while concluding success.
A content-identity optimisation cannot explain it: #7970's nav entry changes every page's
bytes, so any page the run rebuilt would carry it. **Why the 09-25 nightly went partial is
NOT established by this evidence and is an open question owned by the `daily.yml` lane, not
by this postmortem.** What the render outage explains is why the split PERSISTS: `render.yml`'s
`scope=all` pass (the defensive full render at `.github/workflows/render.yml:583`, which a
watermark this far behind forces) is the one act that rewrites the whole estate at once, and
that act is the thing the dead label has made impossible. The restore lever below is unchanged;
its justification is "sweeps the whole estate in one act", never "these pages have no other
baker".

The 111 top-level pages include `china.html`, `hk.html`, `intl.html`, `canada.html`,
`start.html`, `options.html`, `sector_central.html`, `crypto.html`, `ai_desk.html`,
`mastermind.html` and every `strategy_*.html`. **The nav entry is only the probe** — any
template, CSS or builder change merged since `2026-09-23T12:05Z` is equally unpropagated to
those pages. Note `site/aibrief.html` is in the stale set, so #7970's own aibrief band is
not live either.

This does not need a heal PR: the render lane's `pick` step diffs per-region
`(scope=X, from=SHA)` watermarks, so **one successful render after the carrier returns
re-bakes the whole backlog**. Splicing pages by hand (as #7996 did for the one page a byte
guard reddened) is a heal for a *blocked gate*, not for this.

## 3. Why every instrument stayed silent for three days

This is the part worth keeping. Each guard was silent for its own structural reason, and
each reason is correct in isolation.

* **`scripts/check_nightly_liveness.py`** watches `daily.yml` and nothing else. daily.yml
  ran green all three days, so the dead-man switch correctly said nothing. *A per-lane
  watchdog can only cover the lane someone thought to name.*
* **`check_runner_policy.py` R11** passed: `render-linux` **is** declared in the registry.
* **R12** — the rule written for precisely this class after 2026-08-17 — was skipped
  twice over:
  * its gate is `"schedule" in triggers(document)`, and `render.yml` /
    `engine-render.yml` are **push-only**, so it never looked at the label;
  * `sector-intelligence.yml` *does* carry `schedule:`, and was let through only because
    the registry's status string read **`offline`** rather than `orphaned`.
* **The lanes emit nothing.** A run whose job is never assigned produces no logs, no
  annotation and no failure. It is indistinguishable from a quiet night until GitHub kills
  it 24h later.

### The deeper reason: a declaration gate cannot see a death nobody recorded

`.github/runner-policy.yml` is, by its own header, "the STATIC, checked-in model of the
pool, not a liveness probe… `status` is operator-maintained documentation". R11/R12 fire
when a **human writes a death down**. Nobody did — so the rules had nothing to fire on.
Measured drift against the live pool (the file said "Verified against the live pool
2026-08-17", 39 days stale):

| label | declared | live |
|---|---|---|
| `render-linux` | `offline`, pc-render-2/3/4 | **NONE** |
| `Linux` | `offline`, pc-render-2/3/4 | pc-ci-1..4, pc-render-1 |
| `X64` | `offline`, pc-render-2/3/4 | pc-ci-1..4, pc-render-1 |
| `m1-theta` | `orphaned`, [] | **m1-nightly-2** — the canary's own condition was met and nobody noticed |
| `self-hosted` | 4 macs | 12 hosts |

And the file contradicted **itself**: `pool_topology.pc-render` declared `slots: 1` with
`labels: [self-hosted, Linux, X64, render-linux]` — one live routable render host — while
`label_registry.render-linux` said offline with no live carrier.

The `offline` carve-out's premise is the load-bearing error. `offline` means *"registered
and returns"* (the PC pool powers down between canary waves). For `render-linux` neither
half was true: pc-render-2/3/4 had been absent five weeks, and the one live host had been
de-labelled. **A label with zero carriers is `orphaned`, whatever the reason.**

## 4. What this PR changes

1. **`scripts/check_runner_queue_hostage.py` (new) — the actual fix.** A dead-man switch on
   the one observable that is universal even when the cause is not: *is any
   self-hosted-addressed job sitting `queued` with no runner assigned?* Label-agnostic,
   lane-agnostic, no calendar anchor, `actions: read` only. It covers every lane we own
   including ones nobody has thought to watch, and it needs no declaration to be correct —
   which is the property R11/R12 lack. Run live against the outage it was written for, it
   returns all three wedged lanes plus a fourth nobody had reported:

   ```
   run 35975623694 job 'rebuild' (sector-intelligence) [render-linux]            queued 23.7h
   run 35989213316 job 'render' (render) [self-hosted,render-linux]              queued 20.2h
   run 35994988547 job 'research-loop' (codex-research) [self-hosted,codex]      queued 17.1h
   ```

   Threshold **8h**: `macstudio` is a two-host pool shared by the nightly, closing-bell,
   asia-close and the close-pass backstop, so a job can honestly wait behind a multi-hour
   bake (daily 1h12m–2h31m; scope=all render 40–85m). 8h is ~3× the worst honest wait and a
   third of GitHub's 24h kill, so it pages with ~16h of rescue margin and cannot be reached
   by a legitimate queue. A false alarm every night is how a dead-man switch dies.
   Blindness (unreadable API, missing registry, undated row) is INDETERMINATE, never a
   breach. Runs as its **own hosted job** in `nightly-liveness.yml`: a watchdog for "no
   runner can take this job" must never need a runner from the pool under test, and a
   `liveness` breach must not be able to mask it.

2. **R15 in `check_runner_policy.py`** — R12's bar for *every* unattended trigger
   (`push`, `schedule`, `repository_dispatch`), not `schedule:` alone. `push` is not the
   softer trigger: main takes ~25 pushes a day here against one cron line, so a push-only
   lane on a dead label wedges harder. Unwaived, it names all three lanes by file and job.
   A dated waiver under either `scheduled_use_waiver` (the original key, which `codex`
   uses) or `automatic_use_waiver` satisfies it; an undated one does not.

3. **`.github/runner-policy.yml` corrected to the 2026-09-25 receipt** — `render-linux`
   → `orphaned`/`[]` with the receipts and the restore owner in its note; `Linux`/`X64`
   → `live`; `m1-theta` → `live` on m1-nightly-2; `self-hosted`'s twelve hosts (pc-ci-4
   deliberately excluded — R14 makes entering a live roster the activation act for the
   fourth PC CI slot); `pc-render` keeps R7's one-slot reservation but now declares
   `missing_labels: [render-linux]` so the reservation cannot read as live capacity.
   The `offline` carve-out comment now says what it costs.

   The waiver minted for `render-linux` silences the **declaration** gate only, so that
   telling the truth in this file does not red main while the restore is operator-gated.
   It silences nothing else: the hostage check pages regardless of waiver state. **Remove
   that waiver in the same act that restores the carrier.**

## 5. Still open — operator authority

**Restoring render capacity was deliberately not done in-session.** Either
`POST /orgs/mastermindx-market-intelligence/actions/runners/15/labels` with
`{"labels":["render-linux"]}`, or bring a labelled render host back. Two reasons it is not
a session act:

1. **The strip has no recorded cause.** The registry independently declares the render pool
   `offline` and never lists pc-render-1 at all, so de-labelling it may be a deliberate
   repurposing. Silently re-adding a label to shared org infrastructure would override a
   decision nobody has shown me — the same class of error as re-enabling a VPS pull loop
   that was commented off under a `MMX-DISK-TRIAGE-HOLD` marker.
2. **It is a production act with immediate effect.** The label releases a queued `scope=all`
   bake *plus* a three-day scope-union backlog onto a host, at once.

The tempting in-repo alternative — re-pointing the lanes' push default to `render-heavy`
(`mac-builder-light`) — was also **not** taken. That host also carries `macstudio`, so it
would put a 40–85m serial render into contention with the nightly, closing-bell and
asia-close on a two-host pool, and `ci.yml`'s own comments record render traffic starving
`merge-on-green` before. Redirecting production capacity is a capacity decision, not a bug
fix.

Also open, and now visible rather than inferred:

* **`codex-research.yml`** has been queue-wedged on the `codex` label (17.1h at
  measurement, run `35994988547`). Legal today under `codex`'s existing
  `scheduled_use_waiver`, whose stated reasoning — "a queued firing sits `pending` and is
  superseded rather than holding the group" — is contradicted by an actual 17h queued job.
  Worth a re-read now that the symptom is observable.
* **Run `35819881039`'s real red** — `guard — stock dossier integrity (sentinel + identity)`
  — was the last render to execute and it FAILED. Restoring the carrier will surface that
  guard again on the first bake. It is a separate defect and is not fixed here.
* **`.github/runner-policy.yml` cannot self-verify.** Nothing compares its
  `pool_topology` against its `label_registry`. A cheap internal-consistency rule (a pool
  with `slots >= 1` may not claim a label the registry calls orphaned unless it is in
  `missing_labels`) would have flagged the self-contradiction at PR time; the test added
  here pins the pc-render case but the general rule is not built.
