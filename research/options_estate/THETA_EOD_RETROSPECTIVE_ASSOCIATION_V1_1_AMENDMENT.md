# Theta EOD retrospective association v1.1 — pre-outcome determinism amendment

This is a new protocol revision, not a claim that v1 remained unmodified. It supersedes protocol SHA-256 `384d3da6539960cbd768dd1a98eb9bd7b3f87e838fad980caca5f153a9c0a0c3` before any real-data, target, IC, p-value, or outcome summary access. V1 remains preserved.

V1.1 keeps the ten feature formulas and 60 registered cells unchanged. It fixes only deterministic selection, manifest identity, HAC computation, split seams, tied/constant rank statistics, and effective-block order. Selected inputs are exactly Greeks/OI slots for 23 frozen roots and years 2017-2025, plus price slots for SPY and the 20 scored roots. Missing slots are explicit and a missing/present transition refuses analysis. SPX/SPXW are headers-only coverage roots. Other files cannot add candidates.

The canonical manifest uses only source-relative identities and canonical compact JSON serialization; absolute source paths and filesystem stat metadata are not part of its identity. Preparation and analysis require identical selected slots and bytes.

HAC uses the specified full canonical-session zero-residual vector, observed-date denominator, no pair-count normalization or finite factor, and Student-t `df=n-1`. Constant feature or target dates do not become IC dates. Existing `_has_split_seam` is called independently for native root and SPY fill indices, while the era-end purge remains separate. Effective support greedily chooses non-overlapping inclusive label windows, so a later `e0` must be strictly after the previous `eh`.

This amendment remains `PIT_UNPROVEN`, retrospective-only, fit-free, and non-executable. No actual study run has occurred.
