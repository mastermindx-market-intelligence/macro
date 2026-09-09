# RRU international adapter: preserve the actual visible assessment

Same PR6989 research candidate and fixtureeb9e919. No source installation or live data.
After force qualification passed, source tracing found a real outer-consumer gap:
scripts/build_international_macro.py:_radar_display discards every snapshot without
state or h21 odds. The corrected candidate intentionally withholds odds, so direct
card tests can pass while every affected international page removes that very card.
The fallback tile can then show a separate unqualified pullback number. The section
heading also unconditionally claims market-calibrated odds.

Freeze before new tests: the existing adapter must retain explicit composition-bearing
snapshots (including unavailable readings) through the canonical _radar_to_rd mapper.
Preserve old no-record/no-odds legacy behavior; do not synthesize a missing observation.
The existing wrapper must describe an unpromoted construction as an input-based reading,
not calibrated odds. Keep its markup/layout, canonical card and fallback precedence.
Tests call the actual adapter and render the exact owning Jinja section/fallback blocks
with synthetic inputs, including legacy controls. These are not full-page build or
production/entitlement proof. No new risk engine, renderer, score or policy is added.
A separate attempt to list inherited international test files was platform-blocked;
that enumeration was not rerun and no claim about those unseen tests is made.
