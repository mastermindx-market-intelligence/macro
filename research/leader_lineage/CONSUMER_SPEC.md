# Leader lineage — integrated consumer specification (read-only; Leader Radar / Terminal / Prophet)

**Status:** specification only. No consumer is wired in phase 1. Each consumer change is its own PR by
the surface's owner, after #8750 is on `origin/main` and the Leader Pivot owner (#8649) has admitted
the read path. Nothing in this document creates an endpoint, a ledger, a rank, a gate, a size, a trade
or an alert. Source of the descriptor: `engine/leader_lineage.py` (`SPEC_V1.md`).

## 1. Shared rules for every consumer

1. **Two chips, never one.** `thesis_state` and `setup_state` are rendered as two separate chips; no
   consumer may merge them into a single "status". An `UNKNOWN` thesis is never styled as healthy.
2. **Dates come from the episode, not from the consumer.** The historical strip reads
   `leadership_qualified_at → correction_trough_on → (reclaim_50d_on, reclaim_200d_on, …) → closed_on`
   from the `episode` object. Consumers never recompute or infer dates.
3. **Reconstructed is labelled reconstructed.** While `evidence_mode == RECONSTRUCTED_CURRENT_VINTAGE`,
   every surface carries a plain-word "reconstructed from today's history" note; no "first seen" or
   "observed on" wording.
4. **PLTR is illustrative.** Any retrospective example is labelled ILLUSTRATIVE and is never a positive
   label, a pick, or a recommendation.
5. **Glance tier is plain words.** Internal state names (`STRUCTURAL_BREAK`, `R4b`, `ladder_stalled`,
   `PRICE_RS_PROXY`) never appear on the glance tier; they live in hover/popover/detail tiers. Every
   glance panel answers "so what do I do", including the honest "watch — don't chase".
6. **EN/ZH parity and both themes.** Every visible string ships in both languages; no translated text in
   `title=` attributes; dark and light are two art directions, each judged as a design, with the
   evidence matrix (dark/light × EN/ZH × 1440/390) committed under `mockups/evidence/<slug>/`.
7. **Descriptive only.** `authority` is all-false and is forwarded, never dropped: a consumer that
   cannot show the authority block must not show the descriptor.

### Plain-word glance vocabulary (frozen with the spec)

| Internal | Glance (EN) | Glance (ZH) |
|---|---|---|
| thesis `INTACT` | leadership intact | 领导地位完好 |
| thesis `DAMAGED` | leadership damaged | 领导地位受损 |
| thesis `CONTRADICTED` | leadership contradicted | 领导地位被推翻 |
| thesis `UNKNOWN` | leadership unproven | 领导地位待证 |
| setup `WATCH` | watch — don't chase | 观察，勿追 |
| setup `RESET` | resetting | 重置中 |
| setup `REBUILDING` | rebuilding | 重建中 |
| setup `RE_IGNITION` | re-ignition | 再点火 |
| setup `EXTENDED` | extended | 过度延伸 |
| setup `INVALIDATED` | invalidated | 已失效 |

## 2. Payload contract (phase 2, attached by the Leader Radar builder)

Additive to the existing `leaderradar/radar.json` (`leader_radar.v1`); no new endpoint, no new file.
The page stays sign-in-locked exactly as today; anonymous readers see the page HTML only.

```
rows[i].display_chips.leader_lineage = {
  "schema": "leader_lineage.v1", "era": "...", "evidence_mode": "RECONSTRUCTED_CURRENT_VINTAGE",
  "authority": {"may_rank": false, "may_gate": false, "may_size": false, "may_trade": false, "may_alert": false},
  "definition_sha256": "<spec digest>",
  "as_of": "YYYY-MM-DD", "state": "ACTIVE|DAMAGED|REPAIRED|FAILED|NO_PRIOR_LEADER|UNAVAILABLE",
  "thesis_state": "...", "setup_state": "...", "break_class": "...|null",
  "contradiction_evidence": [...], "revisable": true|false|null,
  "price_ath": n|null, "rs_ath": n|null,
  "episode": { ...SPEC_V1 §3 fields... } | null
}
lineage_roster = {
  "schema": "leader_lineage.v1", "era": "...", "as_of": "YYYY-MM-DD",
  "definition_sha256": "...", "evidence_mode": "...", "authority": {...all false...},
  "episodes": [ {ticker, episode_id, prior_episode_id, leadership_qualified_at, phase, break_class,
                 correction_trough_on, reclaim_50d_on, reclaim_200d_on, closed_on, close_reason} ... ],
  "counts": {"ACTIVE": n, "DAMAGED": n, "REPAIRED": n, "FAILED": n, "UNAVAILABLE": n},
  "coverage": {"issuers": n, "with_peer_basket": n, "with_fundamentals": n, "with_volume_demand": n, "with_pivot": n}
}
```

Builder obligations (phase 2 PR, builder owner): wrap the lineage layer in its own `try` so a failure
leaves the incumbent payload byte-identical and emits a bare `::warning title=leader_lineage::…`;
feed `peers` from the existing radar universe (leave-one-out), owner rows only from published owner
descriptors; never read intraday data; never change `rows[i]` ordering, `us_leader_pullback`, or any
existing chip.

## 3. Leader Radar (page owner: `scripts/build_leader_radar.py` / `templates/leader_radar.html.j2`)

- One additive section, same glass family and tokens as the RS-highs panel; archetype per the master
  design system, density budget respected; no third header, no new palette.
- Historical strip per issuer: "damaged as-of <correction_trough_on> → repaired <reclaim_200d_on> /
  re-ignited <rs_vs_spy_rising_on>" or "→ failed <failed_on>" or "→ structural <structural_on>", from
  episode dates only. A stalled ladder renders "evidence incomplete (peer basket)" in plain words.
- Two chips (§1.1). Hover/popover: the ladder with its dates, `ladder_order_violations`,
  `revisable` + `revision_requires`, `price_ath_on` vs `rs_ath_on`.
- The RS-highs panel and the recovery roster shipped by #8750 are untouched; this section is a
  sibling, not a replacement.
- Visual evidence receipt required before merge (`scripts/check_ui_visual_evidence.py`).

## 4. Terminal (owner: charting-app `terminal/lib/flowSource.ts`)

- Reads the SAME payload through the existing radar read path (`f === "radar"`), with the existing
  cold-start fallback shape unchanged; no new endpoint, no new fixture format.
- Renders the two chips and the strip in the issuer drawer only; nothing on the ticker tape.
- A delayed feed is never sold as real-time entry intelligence; the panel header carries the radar
  `as_of` and the reconstructed label.
- The Terminal never computes lineage state locally; a missing `leader_lineage` chip renders nothing.

## 5. Prophet (owner: Prophet board builders)

- Descriptive context only, forwarded with `authority` all-false. No change to rank, selection,
  position size, alerts, entry gate, or source admission — hidden or otherwise.
- The deep-recovery lineage is upstream descriptive context, never a replacement pivot, event
  identity, or admission engine. A future daily label is never used in an earlier intraday pivot.
- Any proposal to promote a lineage field to a ranking or gating input is a separate adjudication with
  the coverage gate (motivating exemplars + current regime, episode-level honest N, in-sample
  disclosure, opus red-team) and prospective evidence.

## 6. Evaluation design (findings, never labels)

- PIT membership: cohorts formed from rows as they would have read on their own `as_of`.
- Matched controls: shallow-reset winners (never below the 200d, drawdown under 10 %) and true-failure
  controls (`FAILED_BREAK` without later re-admission), matched on era, sector and size bucket.
- Rejection / no-signal evidence reported alongside hits; delistings and missing panel members named.
- Forward outcomes net of cost at frozen horizons; episode-level N, not fires.
- Results are published as research findings with the negative headline preserved; they are never
  written onto a row, a chip, or a roster.
