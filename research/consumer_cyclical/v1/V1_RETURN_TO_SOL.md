# Consumer Cyclical V1 — return to Sol

**Operation:** `gmi-consumer-cyclical-v1-integration-20260924-fable-001`
**Principal:** Fable integration owner
**Carrier:** PR #7942 (**MERGED** 2026-09-24T13:07:49Z, `6e3e8987c5c6`), branch
`claude/consumer-cyclical-v1-plnt`; follow-up repair PR #7945, branch `claude/consumer-cyclical-v1-lead`
**Source packet:** R15 `FABLE_INTEGRATION_READY_R15.md` @ `3d286719` (PR #7804, DRAFT/HOLD, research only)
**Admission edge:** deliberate live direct Chairman handoff, 2026-09-24 (see boundary spec §0)

## 1. Delivery state — stated at the rung the evidence reaches

**`V1-CORE` delivered; `V1 PROVEN_LIVE` NOT reached and not claimable.**

R15's V1 ruler requires an entitled user to open PLNT in a browser and see a source-bound explanation.
That cannot be reached today without violating R15's own prohibitions, so it was **not attempted**.
What is delivered is the deterministic, source-coordinate-bound economic core the blocked legs will
later publish unchanged.

Ladder position: **`MERGED` and `PRODUCTION_PROOF` reached; `ACCEPTANCE` is Sol's and is not claimed.**
PR #7942 squash-merged to `main` at 2026-09-24T13:07:49Z as `6e3e8987c5c6`, and the golden oracle was
re-run **from `main`**, not from the carrier branch — see §4. `PRODUCTION_PROOF` here means the module
computes the accepted economics correctly on the canonical tree; it does **not** mean V1's browser
ruler was met, which §1's first line already denies and §6 keeps blocked.

## 2. Why legs 6-9 were frozen rather than built

Every external owner head is **byte-identical to the R15 freeze pins and still OPEN/DRAFT**:

| Owner | head | state |
|---|---|---|
| #7870 shared foundation | `3e3a7956d014` | OPEN draft |
| #7780 build-out ruling | `b68069b2e129` | OPEN draft |
| #7669 template owner | `6942b2b62bad` | OPEN draft |
| #7462 theme graph/store | `31706d7322af` | OPEN draft |
| #7426 company history | `7bc04876747d` | OPEN draft |

`#7331` is named by R15 but is a GitHub **issue**, never pinned to a SHA, and R15 line 148 exempts PLNT
from LULU history. The R15-pinned shared transport `app/theme_research.py` **does not exist on `main`**
(`git rev-parse origin/main:app/theme_research.py` -> exit 128); it lives only on #7870's branch.

`app/earnings.py` was evaluated as an alternative and **rejected on authority, not ignorance**: R15 H1
superseded direct Earnings delivery for this dossier, pre-labels that surface "not a second publisher",
and `engine/earnings_narrative/**` belongs to sibling CDV-1 (#7792).

## 3. What was built, and the precedent it follows

`V1-CORE` extends the already-merged `contracts/sector_intelligence/` family, following the Finance
T1/T2/T3 idiom that landed on `main` the same day while #7870 stayed blocked (#7896 `b4c6e4bd`,
#7920 `e4ac3730`, #7900 `3ca9c303`). It mints no shell, evidence, rights or transport vocabulary.

Changed paths: the contract schema, its fixture, its contract tests, the projection module, its tests,
one exclusive CI job, its `CURATED_EXCLUSIVE` registration, the boundary spec, one `DEC`, one `WS` and
one handoff.

**Gates preserved, not bypassed:**
- no `profile`, no `content_discriminator`, no route, no publisher, no pointer — R15 H2 stays
  `PENDING_SHARED_OWNER_ACCEPTANCE` for the #7780 ruling;
- the contract is named `consumer_cyclical_intelligence_read_model.v1`, mirroring the merged Finance
  axis, so no shipped identifier carries the reserved `economic_change` stem;
- no source collection — the R8 denial is not re-homed.

## 4. Proof

| claim | command | result |
|---|---|---|
| Golden oracle exact, document contract-valid | `pytest tests/test_consumer_cyclical_projection.py tests/test_consumer_cyclical_intelligence_read_model_contract.py -q` | **61 passed** at merge; **65 passed** with the §5a repair |
| Shared contract family still enumerates | `pytest tests/test_sector_intelligence_contracts.py … -q` | **274 passed** |
| CI curation intact | `pytest tests/test_ci_pack.py -k "exclusive or curated" -q` | **7 passed** |
| Pack manifest valid | `run_ci_pack.py --validate-only` | **rc=0**, 229 jobs |
| Records schema-clean | `python3 scripts/agentos.py validate` | **0 errors** |

R6 §7.1 golden values, USD thousands, `Decimal` only, zero `float(` calls:
`total_revenue_change 24344`, `advertising_revenue_change 10141`, `advertising_expense_change 10145`,
`advertising_net_change -4`, `advertising_current_period_net 0`,
`advertising_share_of_revenue_change_pct 41.66`. The two advertising changes both round to `$10.1M`;
the **-4 residual is asserted to survive**.

READY document: 0 schema errors. Zero-facts document: 0 schema errors, `results: []`,
`availability: unavailable`.

## 5. Independent review

An independent Opus review returned **FAIL** on the first boundary packet. All findings accepted and
repaired in `3a0a4bb6`: the unrecorded admission edge, a false "all six owner heads" receipt, and the
contract-name collision with the reserved H2 grammar. Seat verification then found four defects in the
fabric-delivered projection that its own green suite could not detect — its fixtures encoded
`native_admitted: true`, a state that cannot occur for PLNT — repaired in `4f00e7f3`.

### 5a. A defect that only live verification could find (post-merge)

Verifying from `main` after the merge — rather than trusting the green suite — caught a real defect the
61-test suite could not see. `_build_explanation` tested the `FACT_KEY_*` constants for membership in
the set of **result** keys. Those two vocabularies are disjoint, so the test could never be true and the
economic lead was **unreachable on every input**: the document always emitted the neutral fallback
instead of the R6 advertising-flow sentence. Every asserted number stayed exact, which is why the suite
stayed green — the numbers were right and the sentence explaining them was missing.

Repaired on PR #7945 with two regression tests. A same-class audit (two defects sharing one root cause —
comparing the wrong *kind* of identifier) then found two further latent instances and hardened both:
result keys were being spelled by concatenating `"_change"` onto a `FACT_KEY_*` constant (the two
spellings coincide today, so a later rename would have retargeted silently), and `by_key` locals were
named for a grouping that had already moved to `metric`. Neither was live; both are now impossible,
pinned by two invariant tests. 61 -> 65 tests.

The new tests were then checked for vacuity by mutation, because a regression test that passes both
before and after the fix is worse than none — it certifies nothing while looking like proof:

| mutation applied | caught by |
|---|---|
| `RESULT_KEY_*` -> `FACT_KEY_*` in `_build_explanation` (the original defect) | `test_full_case_emits_the_r6_economic_lead_not_the_neutral_fallback` |
| a fact key renamed to collide with a result key | `test_result_keys_and_fact_keys_are_never_interchangeable` (plus the whole golden oracle) |
| facts grouped on `key` instead of `metric` | `test_facts_are_grouped_by_metric_not_by_key` |

Each mutation was applied to the real module, the suite run, and the module restored; all three were
caught by the intended test. 65 passed on the restored tree.

**This is the honest cost of the ruler:** `MERGED` was reached before the lead was correct, and only
production verification distinguished them. It is reported rather than quietly folded into §4.

## 6. What Sol is being asked to unblock

1. **#7870** — the T09 EDGAR-family/fail-closed rights correction, plus T08b / T10e / T10f / T11a.
   Until then the rights veto governs almost none of the SEC corpus and no real Consumer assertion may
   cross the shared route.
2. **#7780** — the cross-vertical profile/dispatch/mount ruling that owns the R15 H2 grammar.
3. **#7669** — template/page custody for the company-page consumer.
4. **Incumbent source owner** — native admission of PLNT accession `0001637207-26-000042` /
   `plntq22026pressreleaseex991.htm`. It is retained nowhere today, so every fact ships
   `native_admitted: false` / `native_ref: null`. This is the honest state, not a placeholder.

## 7. Not requested

No V2 LTH, V3 LULU or V4 theme journey. R15 forbids self-authorizing them on a V1 pass, and the next
modifying child takes its own continuation edge.

## 8. Operational note for the next wave — **corrected**

An earlier revision of this section told you the external fabric was largely unavailable from this host
and asked you to close a provisioning gap. **That was substantially wrong, and the error was mine, not
the fabric's.** Correcting it here because you would otherwise have spent the Agent Fabric program's
time on a non-problem.

What I originally reported, and what is actually true:

| I reported | Actually |
|---|---|
| `pool run qwen` refused -> delegation unavailable | The refusal text was `LOCAL_SEAT_REMOTE_REQUIRED host=m2 … local_only=grok,ocfree`. That is an **instruction to use the remote path**, not a refusal. I read it as a dead end. |
| `pool run grok` refused on host load -> no capacity | True, and irrelevant: `m2` is the **seat**, it is `roles=FAIL(seat)` for lanes by design, and it was at load 31.1/24. Remote hosts were idle. |
| `pool remote` exposes no bailian mode, so there is no remote path | The mode list was right, but I obtained it from an **argparse usage string**. `pool hosts` takes a **positional** mode (`pool hosts minimax`); I invoked `pool hosts --mode minimax`, which errors before printing anything. **I never once saw a host-eligibility table** and concluded from its absence. |

Measured now, from this same seat:

- **Capacity was never the constraint.** `pool plan --class execute --need 2` -> `grant_now=2`,
  `wait_est=0s` on *every* pool (bailian, minimax, grok, cursor, glm, go).
- **Two hosts were ELIGIBLE**: `mini2` (score 0.9479, load 1.25, lane-ceiling 0/2) and `mb`
  (score 0.4942). Both reachable over `BatchMode` ssh.
- **Both already carry a macro checkout** at `~/lanes/repos/macro`, with the established lane-worktree
  convention at `~/lanes/wt/<name>`.
- I then tried to place a real GLM review lane on this PR's own head, and got **partway**: a worktree
  was minted on `mb` at `c4bc7a4ce1` (`~/lanes/wt/cc-v1-review`) and `pool remote mb glm …` returned
  **`LEASE_OK pool=glm`** — the lease and placement layers work. It then failed at transport:
  `SUPPORT_STALE_ACTIVE_REFUSED active=2` / `SCP_FAILED rc=75`.

**So delegation IS currently blocked — but for none of the reasons I first gave, and the real ones are
narrow and fixable:**

1. **Only two hosts can ever run lanes.** Of seven, `m2` is the seat (`roles=FAIL(seat)`), `bm1`/`bmb`
   are `lanes-shadow`, `m1`'s window is `CLOSED`, and `pc` is ssh-unreachable. That leaves `mb` and
   `mini2` — so a single busy host halves fleet lane capacity.
2. **`mb` is at its lane ceiling** (`lane-ceiling=FAIL(2<2)`) and refuses to refresh its stale
   executor surface while lanes are active — reasonable, but it makes a saturated host fail at
   transport *after* granting a lease, which reads like a transport bug rather than saturation.
3. **`mini2` — the only ELIGIBLE host, and the picker's top choice at score 0.93 — cannot reach
   GitHub.** `git fetch` dies with `Could not resolve host: github.com` under both a plain and a login
   shell, with no proxy configured, while `nslookup github.com` resolves and ICMP to `1.1.1.1` is 100%
   loss. Its last successful macro fetch was `2026-09-23 21:59`, so this is a **regression, not its
   configuration**. **The eligibility scorer does not measure git egress** — `reachable=PASS` means ssh,
   `tools=PASS(all)` means binaries — so the picker will keep recommending the one host where any lane
   needing a carrier branch is guaranteed to fail.
4. **`remote_sub.sh` requires a `REMOTE_CWD` that already exists** — it neither fetches the carrier
   branch nor mints a worktree, and under `auto` host selection you cannot know which host to prepare.
   A `--branch` flag minting `~/lanes/wt/<id>` on the selected host would remove the manual step
   entirely — and would have to solve (3) to work at all.

Two smaller items: the `pool` wrapper's `hosts` subcommand takes a positional mode while its own
comment reads like a flag, which is what misled me — and a bare `pool hosts` dies with
`line 42: 1: mode` rather than a usage line. `pool pick review` now returns
`MiniMax-M2.7-highspeed`, which is presumably the answer to the earlier `unrecognized_model
MiniMax-M3` launch failure.

**The honest lesson is mine to carry:** I treated a malformed command's error output as a finding about
the world. The instrument was broken and I never positive-controlled it before reporting its null as
evidence.
