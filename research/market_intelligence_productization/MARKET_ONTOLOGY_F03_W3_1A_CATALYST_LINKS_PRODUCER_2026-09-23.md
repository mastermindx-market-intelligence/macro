---
title: "A-F03-W3-1a catalyst links producer"
packet: A-F03-W3-1a
seat: Meta-CEO A
date: 2026-09-23
---

# Catalyst links producer

## What it is

This packet gives `engine/options_catalyst_link.py` its first production caller. `scripts/build_options_catalyst_links.py` runs once a night, after the episode publish step. It takes the session's date-keyed live-flow events, the same stage the episode builder already reads, and binds each event to catalysts. Single-name events get one earnings candidate from `earnings_blackout.assess`, converted with the `fields_from_assessment` rule that a fresh row must carry an age. The knowledge date is the business-day inverse of the age `assess` returns. That age is an index step on the weekday calendar, so a weekend already counts as the next weekday and a weekday holiday stays on the index. A Saturday run and a Labor Day run of a Friday row both stamp Friday. They do not stamp the prior session, and they do not stamp the run date. FOMC decision dates inside the horizon sit on `CalendarContext.macro_catalysts`, not on a per-root map. The builder writes two files under `site/options_catalyst_links/`: one JSONL of link records, and `latest.json`, which carries the binding-state histogram and a path to that JSONL. It does not carry the records. Every authority flag is false, and `is_context_only` is true.

The stock set is `symbols_on_plane` for the stocks plane. The envelope records that source as `stock_identity.plane:stocks`. An empty plane is legal. Every event is then unresolved, and the envelope says `identity_plane_absent`. If the events stage is missing, the builder writes an envelope with `no_event_stage` and exits 0 so the nightly continues.

## What it is not

This is not the options page. `options.html` is packet W3-1b and is not built here. This packet does not rank, score, size, gate, or originate a signal. It does not open a second collector, a second R2 client, or a second event plane. It does not write under `data/`. It does not bind while the page renders. It does not read live-flow surface stamps or `feed_current`. Session discovery is the episode builder's own discovery, and the only event object it then reads is `live_flow/events/{session}.jsonl`.

Availability receipts in that stage are not events. A decision receipt contributes the event inside it. A row with no id, root, or expiry is dropped and counted. The histogram has one key for each of the eight binding states, and those counts sum to the events that were bound.

## The histogram is the W3-1b gate

The consumer packet is chartered only if `BOUND` plus `STALE_CATALYST` is at least 10 percent of the events that were bound, over the first three nightlies. The denominator is `counts.events` minus `counts.dropped_malformed`. That difference equals the sum of `counts.by_state`. The seat reads the three `latest.json` envelopes and decides. This note states the rule. The producer does not decide, and it does not charter the page.

## Reversibility

Delete the `options_catalyst_links` step in `.github/workflows/daily.yml` and the `options-catalyst-links` job in `.github/ci/legacy-jobs.yml`. The binder was already on main. Removing the step and the job removes this caller.
