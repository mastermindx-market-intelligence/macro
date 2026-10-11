# Intelligence contract laboratory — independent challenge

**Disposition: AMEND BEFORE IMPLEMENTATION HANDOFF.** The current-population numerical findings remain accepted. The reviewed prototype has six reproducible contract gaps, represented by thirteen failing synthetic cases. Two additional source/normalization contracts must be enforced before integrating the pieces; two caller premises must remain explicit. None of these synthetic cases establishes that current production data contain the malformed records.

Reviewed script SHA256: `377dde6af13c890d5b694769408ceaea2515e2a0b4018998128eeb86e150d559`. The exact challenged inputs are preserved under [reviewed_source](reviewed_source/contract_lab.py), so a later repair does not erase the evidence. The executable [challenge_intelligence_contract.py](challenge_intelligence_contract.py) and full [CHALLENGE_RESULTS.json](CHALLENGE_RESULTS.json) contain every counterexample and observed result.

## Accepted findings

The original **56 checks reproduce byte-for-byte**, including the exact 24-name V3 control and four-name overlap under the proposed intelligence order on the 125 qualified candidates. The laboratory correctly distinguishes this numerical coverage from actual source-time-qualified production coverage and from investment improvement.

The normal valid cases for known corrections, future corrections, well-formed retractions, measured zero and identical records work as advertised. The actual analyst duplicate census remains a negative finding: **475 groups, all with identical canonical payloads, zero conflicting groups**. This review independently checked the equality of every retained duplicate payload and the census arithmetic. The reported zero consensus/rating/percentile change under physical row reversal remains the parent's hash-bound reader receipt; this review did not make another remote source-reader replay and does not invent a duplicate corruption incident.

## Six demonstrated prototype gaps

| Priority | Contract gap | Executed counterexample and effect | Minimal repair |
|---|---|---|---|
| P1 | Duplicate comparison is not type sensitive | For the same identity/version, Python dict equality treats `value=1` and `value=True` as equal. Numeric-first retains the active fact; Boolean-first suppresses it. Input order therefore changes usable evidence. `1` versus `1.0` also coalesces but produces different selected digests by order. | Compare a type-sensitive canonical representation. Either normalize validated equivalent numbers to one representation or reject nonidentical representations consistently. A Boolean may never coalesce with a measured number. |
| P1 | Known malformed applicability can resurrect stale facts | A revision-1 retraction has valid publication and first-seen timestamps before cutoff, but `effective_from=None`, a malformed string, or a naive timestamp. The selector rejects that revision before choosing versions and returns revision 0 active. `suppressed` is empty. | Separate knowledge time from applicability validation. A known higher revision with indeterminate applicability must quarantine the observation or fail the source contract. It must not silently restore the prior active value. Preserve valid future-effective corrections as a separate pending case. |
| P1 | Future malformed records break earlier replay | Append a record with valid post-cutoff publication/first-seen clocks and an invalid revision, missing ticker or empty source ID. The selector raises before evaluating its clocks. | Discard envelopes proven unavailable at the cutoff before fatal payload identity/revision checks. Retain diagnostics, but keep earlier selected inputs unchanged. Known malformed identities still need an explicit refusal/quarantine policy. |
| P1 | Invalid session identities can qualify | A session record with `observation_session=None` is accepted when the expected value is also `None`. Matching strings `not-a-session` are also accepted. | Validate the expected-session mapping and every required observation session as actual nonempty session identifiers under the owning calendar contract. Invalid equality must not count as evidence. |
| P1 | Source ticker identity disagrees with candidate identity | `600000.SS ` passes source selection as a distinct issuer. It also bypasses the normalizer's duplicate-ticker guard. Adding that alias changes the real `600000.SS` percentile from **0.00 to 0.25** without a new economic observation. | Reuse the canonical issuer-identity boundary before revision grouping and normalization. At minimum reject whitespace aliases consistently with `qualified_order`; use the existing venue/ticker canonicalizer in integration. |
| P1 | Large numeric values escape the defined error model | A valid JSON integer `10**400` causes `math.isfinite` to raise `OverflowError`. In `qualified_order`, the result is an exception rather than atomic fallback. In a known source correction, it escapes suppression. | Guard conversion/finite checks and convert representability failures into `ContractError`. For bounded intelligence, range validation can reject oversized integers before floating conversion. Preserve latest-known suppression semantics. |

These are thirteen variants of six issues, not thirteen distinct production incidents. P1 here means the contract should be amended before handing the prototype to an implementation owner as settled behavior.

### Why the stale-fact case matters

The earlier amendment correctly stopped filtering invalid numeric payloads or expired revisions before version selection. That same protection does not yet cover applicability clocks. Both `published_at` and `first_seen_at` can establish that the system already knows a higher revision exists. An invalid `effective_from` then makes the revision's applicability uncertain; it does not prove the previous fact remains authoritative.

The safe rule is narrow: preserve an old decision against information demonstrably unavailable at that old cutoff; preserve a current value while a valid correction is explicitly future-effective; quarantine an observation when a higher revision is already known but its applicability cannot be determined. Do not substitute publication time for a missing applicability timestamp or infer retraction semantics from an unqualified row.

### Why exact duplicates need canonical types

The Boolean witness is a silent inconsistency, not merely a digest formatting difference. The existing strict numeric validator rejects `True` when that row becomes selected, but duplicate coalescing can skip the validator for the same row depending on physical order. Fixing the comparator must therefore precede or preserve later payload validation. It must not turn invalid higher revisions into rows discarded early enough to resurrect an old version again.

## Contracts still missing between the tested pieces

**Cadence must come from the source owner.** The API accepts expected sessions, but cadence is self-declared by each row. A stale January observation in a family configured in `expected_sessions` becomes acceptable when its row changes `cadence` from `session` to `periodic`. The lab deliberately supports periodic facts, so the issue is not that old periodic information should expire arbitrarily. It is that the prototype lacks an authoritative family-to-cadence/validity contract capable of distinguishing a real periodic source from a fast source reclassifying itself. Pass the existing owner's versioned contract into selection; do not create a new feature-store owner.

**Normalize compatible feed populations separately.** `source_snapshot` may legitimately return observations from several families. The nested `normal()` helper only verifies distinct tickers. Given one valuation observation and one margin observation for different tickers, it computes a common percentile population across **percentile and CNY units**. The design says normalization is per feed, so the helper must enforce that premise or route observations into existing per-feed aggregation first. A ticker-unique mapping alone is insufficient. Normalization identity should bind the feed/measure and its contract version, qualified aggregation, reference population and cutoff. The current helper is a laboratory demonstration; this is not a claim that a deployed reader currently pools those two sources.

Two additional caller premises are properly separate from those failures:

- `qualified_order` consumes supplied pre-cap qualification. It does not recompute admission. The 125-row current control is valid evidence for this observation, not proof of a general raw-candidate admission implementation.
- Numeric coverage does not establish generation compatibility. The function accepts different arbitrary intelligence-generation labels and contradictory score/rank metadata because it does not check them. The current dataset contains no demonstrated contradiction. Before integration, the existing producer must bind score, incumbent order, intelligence feature generation and decision identity. Otherwise even all-zero intelligence can sort differently from supplied incumbent ranks on inconsistent input.

These premises should be explicit assertions at the existing producer boundary. They do not warrant a parallel candidate engine or new ranking authority.

## Acceptance for the amendment

Keep the existing 56 controls and add the challenge cases to the reviewed laboratory. Acceptance requires:

1. Both orders of numeric/Boolean duplicate witnesses produce the same explicit conflict or safe refusal. Numerically equivalent representations either canonicalize identically or are consistently rejected; their digests cannot depend on physical order.
2. Proven future records with malformed payload identities leave earlier selected inputs unchanged, while known malformed records remain explicit failures.
3. Known higher revisions with missing/invalid applicability suppress or quarantine the observation. Valid future-effective revisions continue to preserve the current valid version. Known invalid payloads and retractions must still never restore an older fact.
4. Missing/malformed expected sessions fail the contract, and fast-family records cannot opt into a periodic exemption. Legitimate previous-session sources and legitimate long-lived periodic facts still qualify under their own owner contracts.
5. Canonical issuer aliases cannot add normalization population weight. The normalizer rejects or separates incompatible feed/measure populations and still refuses multiple unaggregated observations for the same issuer.
6. Every out-of-domain or unrepresentable number uses the defined error path. Intelligence remains atomic, measured zero remains valid, and the current V3 reproduction remains exact.
7. The integrated experiment explicitly checks same-generation qualification/order/feature provenance before describing the intelligence population as complete. Actual source-time-qualified production coverage remains unproved until real inputs supply the necessary clocks.

No vendor calls, production changes, feature-store installation or ranking activation are required to close these laboratory issues. The parent may amend its prototype and arrange a fresh challenge against the new script hash. This review's fixed failure evidence should remain immutable.

## Reproduction and custody

```bash
python research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/intelligence_contract_review/challenge_intelligence_contract.py
```

The script uses the Python standard library, imports the reviewed functions with bytecode writes disabled, and replays the original suite only inside an owned temporary directory. It writes `CHALLENGE_RESULTS.json` in this review directory. It checks all five preserved input hashes before and after the challenge. The final result contains **22 cases: five controls, thirteen failing cases and four explicitly unimplemented boundary cases**. All writes and preserved source snapshots remain within the authorized review directory. The completed matched-controls package and the original intelligence laboratory are untouched by this reviewer.
