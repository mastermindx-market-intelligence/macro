# Market Ontology — F03 Payoff Lab Consumer — 2026-09-23

The F03-W2-5b CONSUMER for the index-ETF payoff lab. This file is the on-disk
copy of the spec's §B copy tables + verdict truth table + the data path the
seat uses for liveness. The full consumer contract lives in the spec; this
file is the canonical artifact for the consumer surface.

## Producer → consumer contract

Producer (W2-5a, store-host, PR #7759, DRAFT, seat-gated): `engine/options_payoff_lab.py` + `scripts/build_options_payoff_lab.py`. SCHEMA `mastermind.options_payoff_lab/v1`. The producer publishes `data/options_payoff_lab/latest.json` on the store host (R2) and re-emits `site/options_payoff_lab/latest.json` on every render.

Consumer (W2-5b, this packet): `scripts/build_options_command.py::build_payoff_lab()` → fold markup in `templates/options.html.j2` → CSS under `.oew-lab*` prefix.

## Data path (engine-render lane)

```
producer (store host, theta-m1)
  ↓ engine.options_payoff.StructureSummary + engine/options_payoff_lab.SCHEMA envelope
data/options_payoff_lab/latest.json
  ↓ R2 publish (scripts/build_options_payoff_lab --accrue)
R2 bucket (mastermindx-prod-artifacts)
  ↓ engine-render.yml: "restore options_payoff_lab from R2 (W2-5a store-host producer)"
scripts/fetch_r2 --dirs options_payoff_lab
  ↓ engine-render.yml cl_gex band: brun options_payoff_lab scripts.build_options_payoff_lab --emit
site/options_payoff_lab/latest.json
  ↓ scripts/build_options_command.load_payoff_lab(root)
build_payoff_lab(payload, stores) -> {sym: card_dict}
  ↓ {% for ix in indexes %}{% set lab = payoff_lab.get(ix.sym) %}{% if lab %}…{% endif %}
templates/options.html.j2 fold markup (under .oew-ic-foot)
  ↓ site/options.html
VPS (3-min pull) → live at /options.html
```

## §B copy tables (the fold's closed vocabulary)

### Row names + what-lines (fixed order, plain EN + ZH)

| Slug | EN name | ZH name | EN what-line | ZH what-line |
|---|---|---|---|---|
| `atm_straddle` | Straddle | 跨式 | pays if the index moves more than the cost, either way | 指数向任一方向的波动超过成本即获利 |
| `rr25` | Upside for downside | 以下行换上行 | buy an upside call, pay for it by selling a downside put | 买入上行看涨，卖出下行看跌以支付成本 |
| `put_spread_95_90` | Downside hedge | 下行保护 | pays if the index falls 5–10%; the cost is the most you can lose | 指数下跌5–10%时获利；最多损失成本 |
| `call_spread_105_110` | Upside play | 上行押注 | pays if the index rises 5–10%; the cost is the most you can lose | 指数上涨5–10%时获利；最多损失成本 |

The slugs never appear on the face (B5). The fixed name is what the reader sees.

### Wall-bracket verdict (closed vocabulary, four plain-word outcomes)

| Condition (lo/hi = sorted straddle breakevens; walls = gex.summary.{put_wall,call_wall}) | EN verdict | ZH verdict |
|---|---|---|
| `lo > put_wall AND hi < call_wall` | Priced move stays inside the walls | 定价波幅在墙位之内 |
| `hi >= call_wall AND lo > put_wall` | Priced move reaches the ceiling | 定价波幅触及上方墙 |
| `lo <= put_wall AND hi < call_wall` | Priced move reaches the floor | 定价波幅触及下方墙 |
| (otherwise — both breached) | Priced move clears both walls | 定价波幅越过上下墙位 |

Track domain = `[min(put_wall, lo) − 2%·spot, max(call_wall, hi) + 2%·spot]`. The walls are measured at this close, the breakevens are at expiry — the lens tip in the markup spells this out so the user does not mistake a to-expiry price for a same-day wall.

### Cost-sign vocabulary (per-share display)

| Sign of `StructureSummary.cost / 100` | EN | ZH |
|---|---|---|
| `> 0` (debit) | costs $X.XX a share · Y.Y% of the index | 成本 $X.YY/股 |
| `< 0` (credit) | brings in $X.XX a share | 获得 $X.XX/股 |
| `= 0` / `None` | cost unavailable | 成本暂不可用 |

Cost is PER-SHARE — `StructureSummary.cost` is per-CONTRACT (`sum(leg.qty * leg.multiplier * leg.entry_price)` at engine/options_payoff.py:949-950), divided by the index-ETF standard multiplier (100, `engine/options_payoff_lab.py::ETF_STANDARD_MULTIPLIER`). See DEC-F03-W2-5B-PAYOFF-LAB-CONSUMER-IS-A-CARD-FOLD.

### Banned-on-the-face vocabulary (B5)

The fold's visible text NEVER carries: `delta`, `vega`, `theta`, `greeks`, `risk reversal`, `ATM`, `25d`, `atm_straddle`, `rr25`, `put_spread_95_90`, `call_spread_105_110`, `display-tier`. The word `mid` is also B5-banned in isolation; the spec's literal footer copy is "End-of-day mid prices, … · ThetaData" (B3 §3) so the token is expected in that one compound phrase and one occurrence is the test's whole allowance.

### Breach-of-fold (when the straddle is NULL)

When the producer's straddle returns `max_gain=None AND max_loss=None`:
- The fold summary flips to the fallback: "What a structure pays" / "结构的盈亏".
- Each row of the four-row table that the producer marks `built=False` (its expiry_payoff has null max_gain and max_loss) renders `class="oew-lab-row is-null"` with a single `<span class="v oew-lab-null">` carrying either the spec's default copy ("not priced today — one leg had no quote" / "今日未定价——某一腿无报价") or the producer's own `states[].reason` when that prose is ≤ 10 plain words.

## Liveness recipe (for the seat)

After the first nightly with a real artifact, the seat can verify the consumer is wired:

```bash
# 1. The producer wrote the site file.
git show origin/main:site/options_payoff_lab/latest.json | python3 -c '
import sys, json
d = json.load(sys.stdin)
print("ledger_asof:", d.get("ledger_asof"))
print("accrual_state:", d.get("accrual_state"))
print("n:", d.get("n"))
'

# 2. The consumer rendered three folds (SPY, QQQ, IWM).
gh api repos/mastermindx-market-intelligence/macro/contents/site/options.html \
  | jq -r '.content' | base64 -d > /tmp/options.html
grep -c 'class="oew-aib-detail oew-lab"' /tmp/options.html
# Expect: 3 (one fold per index ETF the producer priced)

# 3. CI job passed.
gh pr checks <PR>  # options-payoff-lab-consumer: success
```

## Acceptance greps (verbatim from the spec)

```bash
grep -c 'class="oew-aib-detail oew-lab"' templates/options.html.j2 → 1 (origin: 0)
grep -cE '^\s*\.oew-lab' templates/options.html.j2 → ≥ 8 (origin: 0)
grep -nE '\.oew-lab[a-z-]*:(hover|focus)' templates/options.html.j2 → no output
grep -c 'def load_payoff_lab' scripts/build_options_command.py → 1
grep -n 'scripts.build_options_payoff_lab --emit' .github/workflows/engine-render.yml → 1 line, after build_options_skew --emit
grep -c 'options-payoff-lab-consumer:' .github/ci/legacy-jobs.yml → 1
grep -c 'test_options_payoff_lab_consumer' .github/ci/unrun_test_waivers.yml → 0
```

## Related records

- `agentos/decisions/DEC-F03-W2-5B-PAYOFF-LAB-CONSUMER-IS-A-CARD-FOLD.md` — the why.
- `agentos/workstreams/WS-MARKET-OS.md` — owning workstream.
- `research/options_estate/OEU_MASTERPLAN.md` §2 — workspace's "one page, four modes" charter that the fold keeps whole.
- `templates/options.html.j2` — the fold's home (under `.oew-ic-foot`).
- `engine/options_payoff_lab.py` — producer's frozen SCHEMA.
- `scripts/build_options_payoff_lab.py` — producer's ACCRUE/EMIT shell.