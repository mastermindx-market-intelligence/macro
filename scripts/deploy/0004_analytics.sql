-- First-party analytics tables (mirror of the Terminal repo's supabase/migrations/0004_analytics.sql).
-- Purely additive: CREATE TABLE IF NOT EXISTS + indexes + ENABLE RLS (deny-all). Idempotent.
create table if not exists public.analytics_events (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  client_ts   timestamptz,
  type        text not null check (char_length(type) <= 32),
  site        text not null default '' check (char_length(site) <= 16),
  path        text          check (char_length(path) <= 512),
  ref         text          check (char_length(ref) <= 512),
  ticker      text          check (char_length(ticker) <= 64),
  dwell_ms    integer       check (dwell_ms is null or dwell_ms between 0 and 86400000),
  scroll      smallint      check (scroll is null or scroll between 0 and 100),
  fp          text          check (char_length(fp) <= 64),
  session_id  text          check (char_length(session_id) <= 64),
  visitor_id  text          check (char_length(visitor_id) <= 64),
  user_id     uuid references auth.users(id) on delete set null,
  ip          text          check (char_length(ip) <= 64),
  ua          text          check (char_length(ua) <= 256),
  meta        jsonb
);
create index if not exists analytics_events_created on public.analytics_events (created_at desc);
create index if not exists analytics_events_visitor on public.analytics_events (visitor_id, created_at desc) where visitor_id is not null;
create index if not exists analytics_events_session on public.analytics_events (session_id, created_at) where session_id is not null;
create index if not exists analytics_events_type    on public.analytics_events (type, created_at desc);
create index if not exists analytics_events_ticker  on public.analytics_events (ticker, created_at desc) where ticker is not null;
create index if not exists analytics_events_site    on public.analytics_events (site, created_at desc);
create index if not exists analytics_events_ip      on public.analytics_events (ip) where ip is not null;

-- Identity + soft-attribution coverage. The admin analytics panels resolve a cookie to the
-- account it belongs to (`ident`), and annotate anonymous cookies with the most likely account
-- (`cand`). `ident` is the ONE classifier that is deliberately full-history — "a cookie that
-- ever appeared on a signed-in event" is the documented merge rule, so it cannot be narrowed
-- to the panel's window without silently splitting one person into several.
--
-- Without an index on the pair it reads, that rule has to seq-scan the entire store. Measured
-- on production 2026-11-09 against 302,456 rows / 192 MB:
--     ident (full history) 13,506 ms   <- 81% of the 16.7s Visitors fold
--     bots  (windowed)      4,189 ms
--     excluded (windowed)   1,198 ms
--     cand  chain (windowed)  169 ms
-- `ident` is prepended to sessions(), visitors(), visitor() and overview(), so that one scan
-- was the floor under every analytics tab and pushed Visitors/Sessions past the 9s query
-- budget the admin API enforces. Both columns are in the index, so the whole group-by becomes
-- an index-only scan and — being partial — it never touches the unsigned-in bulk of the store.
create index if not exists analytics_events_visitor_user
  on public.analytics_events (visitor_id, user_id)
  where visitor_id is not null and user_id is not null;
-- `excl_seed` (the operator's own cookies) and the `excluded` anti-join match on user_id or ip
-- and then only ever READ visitor_id off the matched row. Both indexes therefore carry it as a
-- trailing column: without that, each probe is an index scan plus a heap fetch per row, and the
-- operator's own account alone holds 56,593 such events (measured 2026-11-09 — 2,704ms of the
-- 3,137ms seed, against 131ms for the index-only `ident` scan of the same rows).
create index if not exists analytics_events_user
  on public.analytics_events (user_id, visitor_id) where user_id is not null;
create index if not exists analytics_events_ip_visitor
  on public.analytics_events (ip, visitor_id) where ip is not null;

create index if not exists analytics_events_fp
  on public.analytics_events (fp) where fp is not null;
-- `fp_farm` is the single most expensive term in a VISITORS/SESSIONS statement. It asks
-- "for the fingerprints seen in this window, how many distinct visitors and IPs share
-- each one" — a question that spans ALL history, over `fp in (select fp from focus_fp)`.
-- With no `fp` index that membership test seq-scanned the store; measured on production
-- 2026-11-09, the 24h Visitors statement sat at 7.54s / 7.44s and fell to 5.54s / 3.89s /
-- 3.37s once this index existed. Dropping the classifiers entirely takes the same
-- statement to 0.73s, so this is where the remaining cost lives.
--
-- NOTE on fingerprints: the COVERING form of this index — (fp, visitor_id) — was tried and
-- REVERTED. It made each probe index-only, but it also flipped the planner from a hash
-- join to nested-loop index probes over a low-selectivity key, and `excluded` regressed
-- from 7.6s to ~33s. The plain (fp) index below is a different animal and measured well.
-- An index that changes the join strategy is not a free win; measure before changing this
-- one back into a covering index.

alter table public.analytics_events enable row level security;

create table if not exists public.ip_geo (
  ip           text primary key check (char_length(ip) <= 64),
  country text, country_code text, region text, city text,
  lat double precision, lon double precision, asn text, org text,
  is_vpn boolean, is_proxy boolean, is_tor boolean, is_hosting boolean, is_abuser boolean,
  fetched_at   timestamptz not null default now()
);
create index if not exists ip_geo_country on public.ip_geo (country_code);
alter table public.ip_geo enable row level security;
