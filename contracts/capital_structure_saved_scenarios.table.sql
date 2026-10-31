-- Capital Structure Intelligence V2 — per-user saved scenarios (SPEC_U2 §1.3)
--
-- APPLYING THIS FILE IS A HUMAN DB ACT, PERFORMED OUTSIDE THE REPOSITORY:
-- the repo has no migrations home, so an operator applies this contract in the
-- Supabase project (SQL editor), once, before the saved-scenario routes leave
-- their typed 503 (`saved_scenarios_store_unavailable`).  Runbook step:
-- "Saved-scenario enrollment (U2)" in the capital-structure operator runbook —
-- apply this file verbatim in the production Supabase project, then verify
-- with the store's own typed reads (a missing table is `unavailable`, never an
-- empty success).  No code path in this repository executes this text.
--
-- The table is the ONLY persistence behind engine/capital_structure/saved_scenario_store.py.
-- `saved_id` is the contract's digest identity over (user, issuer, scenario,
-- view), so saving the same answer twice is the same row (idempotent upsert).
-- `record` carries the full SavedScenario record (its public form omits
-- user_id; the column copy is the store's own partition key shadow).
-- RLS is enabled with owner-only policies on auth.uid() = user_id; the
-- service role bypasses RLS, so the no-leak user partition is enforced by the
-- adapter module for every per-user read.

create table if not exists capital_structure_saved_scenarios (
    saved_id text primary key,
    user_id uuid not null,
    issuer_id text not null,
    record jsonb not null,
    saved_at timestamptz not null,
    updated_at timestamptz not null,
    last_outcome text,
    last_outcome_generation_id text
);

create index if not exists capital_structure_saved_scenarios_user_saved_at_idx
    on capital_structure_saved_scenarios (user_id, saved_at desc);

alter table capital_structure_saved_scenarios enable row level security;

create policy "owner_select_saved_scenarios"
    on capital_structure_saved_scenarios
    for select
    using (auth.uid() = user_id);

create policy "owner_insert_saved_scenarios"
    on capital_structure_saved_scenarios
    for insert
    with check (auth.uid() = user_id);

create policy "owner_update_saved_scenarios"
    on capital_structure_saved_scenarios
    for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "owner_delete_saved_scenarios"
    on capital_structure_saved_scenarios
    for delete
    using (auth.uid() = user_id);
