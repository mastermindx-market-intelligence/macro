# SNI public-exposure census (PUB, 2026-10-13)

SNI-local DRAFT review. It does not own Data OS identity, Company
Event/Earnings, FIF, Capital Structure, Stock Identity, Options, Research
Vault, or qledger/Evaluation. Identity ids are caller-supplied opaque strings;
this note mints none. Residual and stress statistics, if any, stay descriptive.
Every authority flag stays false: this census does not feed a ranker, gate,
sizer, signal, escalation, or trade path.

Base commit: `040b61c32fc7d1be1f9b0f22d03f6a43540a4fe5` (SNI INT1).

## Summary

No public serving, render, or upload surface on this tree references
`research/single_name_intelligence` or `contracts/single_name_intelligence`,
and no scanned publish/copy rule uses a glob whose source is the repo
`research/` tree. SNI material (study code, sealed runs, protocols, drafts,
reviews under `research/single_name_intelligence/` plus
`contracts/single_name_intelligence/`) therefore cannot ride today's Caddy
root, R2 named-dir upload, or `site/` render commit. The guard test
`tests/test_sni_public_exposure.py` pins that census and fails if a future
template, publish script, or render/deploy workflow grows a leak.

## Public roots

Established from Caddy, VPS update, R2 publisher, and render config. Bucket
and credential values are env-supplied names only; none are recorded here.

| Public root | What it serves | Evidence |
| --- | --- | --- |
| `/opt/macro/site.served` | Static origin for mastermind-x.com (www HTTP/HTTPS snippet `mastermind_static`; also admin `/research-tools/*`) | `app/deploy/Caddyfile:88` `root * /opt/macro/site.served`; `:930` same root behind admin auth |
| `site/` → `site.served/` | Atomic rsync source of the Caddy root | `app/deploy/update.sh:296` `rsync -a --delete --min-size=1 "$APP_DIR/site/" "$APP_DIR/site.served/"`; Caddyfile:83–88 |
| `site/` (render output) | Dashboard HTML/JSON written by the site renderer; `storage.site_dir` | `scripts/build_site.py:1` ("Generate the static dashboard (site/…)"); `config.yml:50` `site_dir: site`; `.github/workflows/render.yml:28` commits ONLY `site/` |
| R2 object prefixes | Browser data plane: named dirs under `site/<dir>` or `data/<dir>`, keys `<dir>/…`, bucket `R2_BUCKET` | `scripts/publish_r2.py:8–13`, `:75–112` `DEFAULT_DIRS` (ohlc, stockdata, intraday, feeds, oddsmatrix, seasonalitydata/entities, …), `:114–116` `_DATA_DIRS`, `:588–615` `base = site / d` or `data / d` |
| `/var/lib/macro-live/public` | Live quotes/breadth/release/staleness JSON | `app/deploy/Caddyfile:196` `root /var/lib/macro-live/public`; `:200–202` `file_server` |
| `/opt/terminal/terminal/public` | Terminal `/data/*` static JSON | `app/deploy/Caddyfile:726` `root * /opt/terminal/terminal/public` |
| `/opt/maltese` | maltese.greydeercapital.com sticker gallery (outside this checkout) | `app/deploy/Caddyfile:1173` |
| `/opt/slate` | slate.greydeercapital.com and notes.mastermind-x.com PWA (outside this checkout) | `app/deploy/Caddyfile:1197`, `:1238` |
| `/opt/greydeercapital` | greydeercapital.com brand site (outside this checkout) | `app/deploy/Caddyfile:1273` |
| GitHub Pages of committed `site/` | Inferred: render commits `site/` to main; VPS/Caddy serves main. `pages.yml` itself was not opened (not in INPUTS) | `.github/workflows/render.yml:28`, `:231` |

Not currently public:

- `/opt/macro/press_research.served` is filled from `properties/research/` (`app/deploy/update.sh:318–320`) but the Caddy `root * /opt/macro/press_research.served` block is commented out (`app/deploy/Caddyfile:1088`). That tree is the D14 press property, not repo `research/single_name_intelligence/`.
- `site.served/` is gitignored (`.gitignore:26–29`) as a VPS-only mirror.
- Heavy per-ticker `site/` stores (ohlc, stockdata, …) are gitignored and published only via the named-dir R2 list above.

`.gitignore:61–66` records that `site/research/` is tracked Research Vault landing pages, a different tree from `research/single_name_intelligence/`.

SNI material on this worktree (names only): `common/`, `e2e_20261011/`, `evaluation/`, `event_response/`, `evidence/`, `protocols/`, `residual/`, `runs/`, `us_stress/`, `us_transfer/`, plus the SNI_E0 / SNI_M0 / SNI_U0 / SNI_V0 qualification notes.

## Hits table

INPUT grep (capped): `git grep -n -e single_name_intelligence -e "contracts/single_name" -- templates/ app/ scripts/ config/ .github/workflows/`

Public-surface count: **0**.

| path:line | class | reason |
| --- | --- | --- |
| `templates/` (no hits) | — | No SNI path string. Templates are copied/rendered into `site/` and would be PUBLIC-EXPOSURE if present. |
| `app/` (no hits) | — | No SNI path string. App code is the API origin behind Caddy `/api/*`. |
| `scripts/` (no hits) | — | No SNI path string in publish/render/upload scripts. |
| `.github/workflows/` (no hits) | — | No SNI path string in workflow YAML. |
| `config/single_name_intelligence/coverage_profiles/alibaba.yml:2` | INTERNAL | Schema comment `contracts/single_name_intelligence/coverage_profile.v1.schema.json`. Coverage YAML lives under `config/`; Caddy rsyncs `site/` only; R2 uploads named `site/`/`data/` dirs; render commits `site/`. Not served. |
| `config/single_name_intelligence/coverage_profiles/alibaba.yml:8` | INTERNAL | Comment pointing at `research/single_name_intelligence/SNI_E0_…`. Same non-served config tree. |
| `config/single_name_intelligence/coverage_profiles/alibaba.yml:9` | INTERNAL | Comment pointing at `research/single_name_intelligence/SNI_M0_…`. Same non-served config tree. |
| `config/single_name_intelligence/coverage_profiles/tencent.yml:2` | INTERNAL | Same schema comment as Alibaba profile. |
| `config/single_name_intelligence/coverage_profiles/tencent.yml:8` | INTERNAL | Same E0 comment as Alibaba profile. |
| `config/single_name_intelligence/coverage_profiles/tencent.yml:9` | INTERNAL | Same M0 comment as Alibaba profile. |

`ALLOWED` in the guard test is empty: those six lines are on `config/`, which the scanner does not treat as a public surface.

## Broad globs

Question: does any publish/upload/static-copy rule use a glob broad enough to include repo `research/`?

**No.**

| Candidate | file:line | Would SNI bytes ride? |
| --- | --- | --- |
| `rsync … "$APP_DIR/site/" "$APP_DIR/site.served/"` | `app/deploy/update.sh:296` | No. Source is `site/`. |
| `rsync … "$APP_DIR/properties/research/" … press_research.served` | `app/deploy/update.sh:320` | No. Source is `properties/research/` (press property). Caddy block commented (`Caddyfile:1088`). |
| `git add site/` (render commit) | `.github/workflows/render.yml:1355` | No. `site/` only; comments at `:28` and `:1328` forbid `data/` and `reports/`. |
| `python -m scripts.publish_r2 --dirs stockdata` | `.github/workflows/render.yml:1247`; `engine-render.yml:846` | No. Named dir under `site/`. |
| `DEFAULT_DIRS` / `_DATA_DIRS` | `scripts/publish_r2.py:75–116` | No. Closed list of `site/<dir>` and `data/<dir>` names. `research` is not a member. |
| `git add data/ site/…` (nightly) | `.github/workflows/daily.yml` (multiple; e.g. `:638`, `:1868`) | No. `data/` and `site/` (sometimes `reports/`). Not `research/`. |

No `research/**`, `"research/"`, `git add research`, or `--dirs research` appears in `PUBLISH_SCRIPTS` or the three render/deploy workflows.

## What the guard does and does not cover

Does:

- Scan `templates/`, `app/` excluding app tests, and `PUBLISH_SCRIPTS` for the two SNI path substrings.
- Scan `PUBLISH_SCRIPTS` plus `.github/workflows/render.yml`, `engine-render.yml`, and `daily.yml` for copy/upload sources of `research`, `research/`, `research/**`.
- Fail the real tree on any unallowed hit (a real exposure is a BLOCKER, not an `ALLOWED` entry).
- Catch a synthetic poisoned template link and a synthetic `research/**` upload.

Does not:

- Scan generated `site/` bytes (mission forbids reading `site/` contents; the tree may be sparse/generated).
- List or fetch R2 bucket contents, VPS disks, or CDN cache.
- Open `.github/workflows/pages.yml` or other workflows outside INPUTS.
- Scan `engine/`, `data/`, `docs/`, `reports/`, `config/` (config hits are census-only, INTERNAL).
- Treat CI path filters such as `research/**` in `ci.yml` as publish rules (CI trigger, not an upload).
- Prove a future glob in an unscanned script cannot leak; it pins the public path that exists today.
