# Seat erratum — CDV-1 Task 2, ruling R4.2a, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`. This record closes a gap the seat left between two of its own packets. It was found by the seat while preparing the round-4 verification, before either fix lane returned.

## The gap

- Task 2 ruling R4.2 says the preparation output's `source_clock` is the acquisition's `checked_at`, and that it "may be `None` only for `currentness_unverified`". That wording permits an unverified state that carries a clock, and the acquisition stamp always has one.
- Task 3 (rulings R4.1 and R5.1) refuses `currentness_unverified` with a `source_clock`. The spec §5.9 unverified template prints no clock.
- Task 4 is ruled to pass Task 2's object into Task 3 with no translation. With the gap open, every unverified acquisition would be refused at Task 3.

## Ruling R4.2a

In the preparation output `currentness_context.currentness`:
- `source_clock` is the acquisition's `checked_at` for `up_to_date` and `newer_source_pending`;
- `source_clock` is `None` for `currentness_unverified`.

The acquisition stamp itself is unchanged: it keeps `checked_at` for every state, so no trace data is lost. Task 3 is unchanged.

## How it is applied

The Task 2 round-4 lane was already running when the gap was found, and a running lane is never relaunched. The seat therefore applies R4.2a to the lane's returned head itself: either the lane's output already satisfies it, or the seat makes one small ruling-derived commit on the same branch, with the unverified round-trip test asserting `source_clock is None`.
