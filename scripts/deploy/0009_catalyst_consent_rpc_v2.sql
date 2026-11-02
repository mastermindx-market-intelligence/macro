-- 0009 — CATALYST POSITIVE EVENT CONSENT v2 (owner-run RPCs + revocation triggers).
-- Extension of the incumbent Supabase email estate (0007_support_email.sql).
-- Apply path: scripts/deploy/catalyst_consent_migrate.py --apply, run ON the VPS with
-- /etc/macro-admin.env sourced (Management API SQL endpoint, same route as 0004).
-- Rollback: 0009_catalyst_consent_rpc_v2_rollback.sql (drops triggers + functions, RETAINS
-- the two ledger tables). Runbook: docs/ops/catalyst-consent-rpc.md.
-- Local proof: python3 scripts/test_catalyst_consent_rpc_review.py (new socket-only cluster).
--
-- Admits no new auth, sender, public queue, license, or marketing-opt-in inference.
-- RPCs match app.catalyst_optin.SupabaseConsentRpcOwner v2 exactly.
--
-- TRUST MODEL. Only service_role can EXECUTE the seven RPCs; no role except the owner
-- can touch the two tables (service_role included: the RPCs are SECURITY DEFINER and
-- run as the owner, so service_role needs no table grant). The application validates
-- the signed HMAC intent and the GoTrue OTP; the database locks the exact pending
-- intent attributes and requires the EXISTING auth.users confirmed ID. The SQL parses
-- HMAC payload fields for binding but DOES NOT forge or verify HMAC; the signature is
-- checked only in the application.
--
-- OWNER ASSUMPTIONS (fenced at the end of this file): the role applying this file owns
-- both tables and all functions, is not a client role, and the tables are not under
-- FORCE ROW LEVEL SECURITY (the owner bypasses the deny-all RLS from inside the RPCs).
-- The Management API and the dashboard SQL editor both run as `postgres`, which holds.
-- The SECURITY DEFINER bodies also read public.email_suppression, public.email_prefs
-- and auth.users as that owner: it must own the two incumbent tables (or hold
-- BYPASSRLS), neither may be FORCE RLS, and it must hold SELECT on auth.users;
-- otherwise the suppression veto would silently see no rows. Fenced below.
--
-- SEMANTICS WORTH KNOWING.
--   * Revocation is permanent per (user, event, scope). A later confirm for the same
--     event finds the revoked grant and raises CONSENT_ALREADY_REVOKED_OR_MISMATCHED;
--     the application surfaces that as a refusal, never as a fresh grant. Re-consent
--     after revoke needs a new scope or event, by design (no "re-subscribe" path here).
--   * Grants reference auth.users ON DELETE CASCADE: deleting the GoTrue user deletes
--     that user's grants and their replay ledger rows. Pending rows are keyed by the
--     signed intent only and are swept one hour after expiry by the next begin() call.
--   * Lock order. confirm() takes the email advisory lock, then the user advisory
--     lock. The address-suppression trigger (on email_suppression) takes only the email
--     lock; the user-opt-out trigger (on email_prefs) takes only the user lock. No path
--     takes the user lock before the email lock, so the three cannot deadlock.
--   * The two incumbent-table triggers never block an incumbent write: a blank address
--     on email_suppression is left to that table's own constraints (the trigger returns
--     NEW untouched); only a lock wait can delay it.
--   * Every mutating RPC refuses NULL or malformed input with a named exception, never
--     a constraint error and never a silent success. catalyst_consent_current is a
--     pure lookup: NULL or unknown keys return NULL (no grant), which the app treats
--     as absent.
--   * Re-apply reconciliation. While the two incumbent-table triggers are absent (a
--     rollback window), an opt-out or a suppression cannot revoke grants; every apply
--     therefore revokes active grants whose user is opted out or whose address is
--     suppressed, so re-applying never resurrects a grant the estate withdrew.

begin;
set local lock_timeout = '3s';
set local statement_timeout = '60s';

create table if not exists public.catalyst_consent_pending (
  public_ref text primary key
    check (public_ref ~ '^[A-Za-z0-9_-]{8,128}$'),
  signed_intent text not null check (length(signed_intent) between 1 and 4096),
  email_tag text not null check (email_tag ~ '^[0-9a-f]{64}$'),
  intent_id text not null unique check (intent_id ~ '^[A-Za-z0-9_-]{20,96}$'),
  event_id text not null check (event_id ~ '^[A-Za-z0-9_.:-]{1,128}$'),
  scope text not null check (scope = 'catalyst_event_updates/v1'),
  tickers text[] not null check (cardinality(tickers) between 1 and 10),
  first_touch jsonb not null check (jsonb_typeof(first_touch) = 'object'),
  created_at timestamptz not null default pg_catalog.now(),
  expires_at_utc timestamptz not null
);
create index if not exists catalyst_consent_pending_expiry
  on public.catalyst_consent_pending (expires_at_utc);
alter table public.catalyst_consent_pending enable row level security;

create table if not exists public.catalyst_consent_grants (
  grant_id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id text not null check (event_id ~ '^[A-Za-z0-9_.:-]{1,128}$'),
  scope text not null check (scope = 'catalyst_event_updates/v1'),
  tickers text[] not null check (cardinality(tickers) between 1 and 10),
  -- Immutable nonce kept independently so expired signed pending-body rows
  -- can be deleted without losing a confirmed grant's replay ledger.
  intent_id text not null unique,
  verified_at_utc timestamptz not null,
  first_touch jsonb not null check (jsonb_typeof(first_touch) = 'object'),
  created_at timestamptz not null default pg_catalog.now(),
  revoked_at_utc timestamptz,
  unique (user_id, event_id, scope)
);
create index if not exists catalyst_consent_grants_event
  on public.catalyst_consent_grants(event_id, verified_at_utc)
  where revoked_at_utc is null;
alter table public.catalyst_consent_grants enable row level security;

-- Private owner data, never a REST surface for ANY key, service_role included.
revoke all on public.catalyst_consent_pending from public, anon, authenticated, service_role;
revoke all on public.catalyst_consent_grants from public, anon, authenticated, service_role;
revoke all on sequence public.catalyst_consent_grants_grant_id_seq
  from public, anon, authenticated, service_role;
-- RLS stays enabled with zero client policies; none is created or relaxed here.

-- A confirmed grant is an append-only ledger row: identity columns never change and
-- a revocation can never be cleared, not even by the owner through a direct UPDATE.
create or replace function public.catalyst_consent_grant_guard()
returns trigger language plpgsql set search_path = ''
as $catalyst_grant_guard$
begin
  if new.grant_id is distinct from old.grant_id
     or new.user_id is distinct from old.user_id
     or new.event_id is distinct from old.event_id
     or new.scope is distinct from old.scope
     or new.tickers is distinct from old.tickers
     or new.intent_id is distinct from old.intent_id
     or new.verified_at_utc is distinct from old.verified_at_utc
     or new.first_touch is distinct from old.first_touch
     or new.created_at is distinct from old.created_at
     or (old.revoked_at_utc is not null
         and new.revoked_at_utc is distinct from old.revoked_at_utc) then
    raise exception 'CATALYST_CONSENT_GRANT_IMMUTABLE';
  end if;
  return new;
end;
$catalyst_grant_guard$;
revoke all on function public.catalyst_consent_grant_guard() from public, anon, authenticated, service_role;
drop trigger if exists catalyst_consent_grant_immutable on public.catalyst_consent_grants;
create trigger catalyst_consent_grant_immutable
  before update on public.catalyst_consent_grants
  for each row execute function public.catalyst_consent_grant_guard();

-- Contract probe: touches no table, so it runs as the caller (no SECURITY DEFINER).
create or replace function public.catalyst_consent_contract()
returns jsonb language sql set search_path = ''
as $$
  select pg_catalog.jsonb_build_object('owner', 'email_consent', 'version', 2)
$$;

create or replace function public.catalyst_consent_begin(
  p_intent text, p_email_tag text, p_expires_at_utc text
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_encoded text;
  v_raw text;
  v_payload jsonb;
  v_nonce text;
  v_event text;
  v_scope text;
  v_tickers text[];
  v_touch jsonb;
  v_issued timestamptz;
  v_expires timestamptz;
  v_ref text;
  v_bad boolean;
begin
  if p_intent is null or p_email_tag is null or p_expires_at_utc is null
     or pg_catalog.length(p_intent) not between 80 and 4096
     or p_intent !~ '^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$'
     or p_email_tag !~ '^[0-9a-f]{64}$' then
    raise exception 'INVALID_PENDING_INTENT';
  end if;
  v_encoded := pg_catalog.split_part(p_intent, '.', 1);
  if pg_catalog.length(v_encoded) > 3000 then
    raise exception 'INVALID_PENDING_INTENT';
  end if;
  begin
    v_raw := pg_catalog.convert_from(
      pg_catalog.decode(
        pg_catalog.translate(v_encoded, '-_', '+/') ||
        pg_catalog.repeat('=', (4 - pg_catalog.length(v_encoded) % 4) % 4),
        'base64'), 'UTF8');
    v_payload := v_raw::jsonb;
    v_issued := (v_payload->>'issued_at')::timestamptz;
    v_expires := p_expires_at_utc::timestamptz;
  exception when others then
    raise exception 'INVALID_PENDING_INTENT';
  end;
  v_nonce := v_payload->>'nonce';
  v_event := v_payload->>'event_id';
  v_scope := v_payload->>'scope';
  v_touch := v_payload->'first_touch';
  -- Every comparison is NULL-safe: a missing field is a refusal, not a pass.
  if pg_catalog.jsonb_typeof(v_payload) is distinct from 'object'
     or (v_payload->>'v') is distinct from '1'
     or v_scope is distinct from 'catalyst_event_updates/v1'
     or v_nonce is null or v_nonce !~ '^[A-Za-z0-9_-]{20,96}$'
     or v_event is null or v_event !~ '^[A-Za-z0-9_.:-]{1,128}$'
     or (v_payload->>'email_tag') is distinct from p_email_tag
     or pg_catalog.jsonb_typeof(v_payload->'tickers') is distinct from 'array'
     or pg_catalog.jsonb_typeof(v_touch) is distinct from 'object'
     or v_issued is null or v_expires is null
     or v_issued > pg_catalog.now() + interval '30 seconds'
     or v_issued < pg_catalog.now() - interval '20 minutes'
     or v_expires <= pg_catalog.now()
     or pg_catalog.abs(extract(epoch from
               (v_expires - (v_issued + interval '20 minutes')))) > 5
  then
    raise exception 'INVALID_PENDING_INTENT';
  end if;
  select pg_catalog.array_agg(e.value order by e.ordinality)
    into v_tickers
  from pg_catalog.jsonb_array_elements_text(v_payload->'tickers')
    with ordinality as e(value, ordinality);
  if v_tickers is null
     or pg_catalog.cardinality(v_tickers) not between 1 and 10
     or (select pg_catalog.count(distinct t) from pg_catalog.unnest(v_tickers) as t)
        <> pg_catalog.cardinality(v_tickers)
     or exists (select 1 from pg_catalog.unnest(v_tickers) t
                where t is null or t !~ '^[A-Z][A-Z0-9.-]{0,9}$')
  then
    raise exception 'INVALID_PENDING_TICKERS';
  end if;
  select pg_catalog.bool_or(k.key not in
            ('utm_source','utm_medium','utm_campaign','utm_content','partner_id')
            or pg_catalog.jsonb_typeof(k.value) <> 'string'
            or k.value #>> '{}' !~ '^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$')
    into v_bad
  from pg_catalog.jsonb_each(v_touch) as k;
  if coalesce(v_bad,false) then
    raise exception 'INVALID_PENDING_ATTRIBUTION';
  end if;

  -- Sweep signed bodies that expired more than an hour ago. The grant ledger keeps
  -- its own intent_id copy, so this never touches a confirmed grant's audit trail.
  delete from public.catalyst_consent_pending
   where expires_at_utc < pg_catalog.now() - interval '1 hour';

  -- 244-bit CSPRNG opaque handle: two independent built-in v4 UUIDs (122 random bits
  -- each), rendered as 64 hex characters.
  v_ref := pg_catalog.replace(pg_catalog.gen_random_uuid()::text,'-','') ||
           pg_catalog.replace(pg_catalog.gen_random_uuid()::text,'-','');
  begin
    insert into public.catalyst_consent_pending
        (public_ref,signed_intent,email_tag,intent_id,event_id,scope,
         tickers,first_touch,expires_at_utc)
    values (v_ref,p_intent,p_email_tag,v_nonce,v_event,v_scope,
            v_tickers,v_touch,v_expires);
  exception when unique_violation then
    -- The same signed nonce can begin exactly once; a replay is refused by name.
    raise exception 'PENDING_INTENT_REPLAY';
  end;
  return pg_catalog.jsonb_build_object('public_ref',v_ref);
end;
$$;

create or replace function public.catalyst_consent_resolve(
  p_public_ref text, p_email_tag text
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare v_intent text;
begin
  if p_public_ref is null or p_email_tag is null
     or p_public_ref !~ '^[A-Za-z0-9_-]{8,128}$'
     or p_email_tag !~ '^[0-9a-f]{64}$' then
    raise exception 'INVALID_PENDING_REF';
  end if;
  select p.signed_intent into v_intent
    from public.catalyst_consent_pending p
   where p.public_ref=p_public_ref and p.email_tag=p_email_tag
     and p.expires_at_utc > pg_catalog.now();
  if v_intent is null then
    raise exception 'PENDING_REF_UNAVAILABLE';
  end if;
  return pg_catalog.jsonb_build_object('intent',v_intent);
end;
$$;

create or replace function public.catalyst_consent_confirm(
  p_user_id uuid, p_event_id text, p_scope text, p_tickers text[],
  p_intent_id text, p_verified_at_utc text, p_first_touch jsonb
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare
  v_pending public.catalyst_consent_pending%rowtype;
  v_record public.catalyst_consent_grants%rowtype;
  v_email text;
  v_confirmed timestamptz;
  v_verified timestamptz;
  v_created boolean := false;
  v_sorted_in text[];
begin
  if p_user_id is null or p_event_id is null or p_tickers is null
     or p_first_touch is null or p_verified_at_utc is null
     or p_scope is distinct from 'catalyst_event_updates/v1'
     or p_intent_id is null or p_intent_id !~ '^[A-Za-z0-9_-]{20,96}$' then
    raise exception 'CONSENT_PURPOSE_INVALID';
  end if;
  select * into v_pending
    from public.catalyst_consent_pending p
   where p.intent_id=p_intent_id and p.expires_at_utc > pg_catalog.now()
   for update;
  if not found then raise exception 'CONSENT_PENDING_NOT_CURRENT'; end if;
  -- Ticker sets are compared order-insensitively (the application does the same);
  -- the stored order is the signed intent's order.
  select pg_catalog.array_agg(t order by t) into v_sorted_in
    from pg_catalog.unnest(p_tickers) as t;
  if v_pending.event_id is distinct from p_event_id
     or v_pending.scope is distinct from p_scope
     or (select pg_catalog.array_agg(t order by t)
           from pg_catalog.unnest(v_pending.tickers) as t) is distinct from v_sorted_in
     or v_pending.first_touch is distinct from p_first_touch then
    raise exception 'CONSENT_INTENT_MISMATCH';
  end if;
  begin
    v_verified := p_verified_at_utc::timestamptz;
  exception when others then
    raise exception 'CONSENT_VERIFIED_CLOCK_INVALID';
  end;
  if v_verified is null or v_verified > pg_catalog.now() + interval '30 seconds'
     or v_verified < pg_catalog.now() - interval '5 minutes'
     or v_verified < v_pending.created_at - interval '30 seconds' then
    raise exception 'CONSENT_VERIFIED_CLOCK_INVALID';
  end if;
  -- Address belongs ONLY to GoTrue. Do not trust browser form email or a
  -- separate shadow contact list. The Python owner has already verified OTP.
  select pg_catalog.lower(pg_catalog.btrim(u.email)), u.email_confirmed_at
    into v_email, v_confirmed
    from auth.users u where u.id=p_user_id;
  if v_email is null or v_email = '' or v_confirmed is null
     or v_confirmed > v_verified + interval '30 seconds' then
    raise exception 'CONSENT_GOTRUE_UNVERIFIED';
  end if;
  -- Fixed lock order (email, then user) shared with this file's two incumbent-table
  -- triggers, each of which takes exactly one of these keys. Taken BEFORE inspecting
  -- suppression and before INSERT, so a READ COMMITTED check-then-insert cannot race
  -- an unsubscribe or an opt-out.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('mmx-catalyst-email:' || v_email, 24001));
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('mmx-catalyst-user:' || p_user_id::text, 24001));
  -- Mandatory additional current suppression veto, not an opt-in inference.
  if exists (select 1 from public.email_suppression s
              where pg_catalog.lower(pg_catalog.btrim(s.email)) = v_email)
     or exists (select 1 from public.email_prefs e
                 where e.user_id=p_user_id and e.marketing_opt_out) then
    raise exception 'CONSENT_ADDRESS_SUPPRESSED';
  end if;

  begin
    insert into public.catalyst_consent_grants
      (user_id,event_id,scope,tickers,intent_id,verified_at_utc,first_touch)
    values (p_user_id,p_event_id,p_scope,v_pending.tickers,p_intent_id,v_verified,p_first_touch)
    on conflict (user_id,event_id,scope) do nothing
    returning * into v_record;
    v_created := found;
  exception when unique_violation then
    -- intent_id is unique across users: one signed intent confirms one user only.
    raise exception 'CONSENT_INTENT_ALREADY_USED';
  end;
  if not v_created then
    select * into v_record from public.catalyst_consent_grants g
     where g.user_id=p_user_id and g.event_id=p_event_id and g.scope=p_scope;
  end if;
  if v_record.grant_id is null or v_record.revoked_at_utc is not null
     or (select pg_catalog.array_agg(t order by t)
           from pg_catalog.unnest(v_record.tickers) as t) is distinct from v_sorted_in then
    raise exception 'CONSENT_ALREADY_REVOKED_OR_MISMATCHED';
  end if;
  return pg_catalog.jsonb_build_object(
    'created',v_created,
    'record', pg_catalog.jsonb_build_object(
      'user_id',v_record.user_id,'email',v_email,
      'event_id',v_record.event_id,'scope',v_record.scope,
      'tickers',pg_catalog.to_jsonb(v_record.tickers),
      'intent_id',v_record.intent_id,
      'verified_at_utc',v_record.verified_at_utc,
      'first_touch',v_record.first_touch,
      'revoked_at_utc',v_record.revoked_at_utc
    ));
end;
$$;

create or replace function public.catalyst_consent_current(
  p_user_id uuid, p_event_id text
) returns jsonb language sql security definer set search_path = ''
as $$
  select pg_catalog.jsonb_build_object(
    'user_id',g.user_id,'email',pg_catalog.lower(pg_catalog.btrim(u.email)),
    'event_id',g.event_id,'scope',g.scope,'tickers',pg_catalog.to_jsonb(g.tickers),
    'intent_id',g.intent_id,'verified_at_utc',g.verified_at_utc,
    'first_touch',g.first_touch,'revoked_at_utc',g.revoked_at_utc)
  from public.catalyst_consent_grants g join auth.users u on u.id=g.user_id
  where g.user_id=p_user_id and g.event_id=p_event_id
    and g.scope='catalyst_event_updates/v1'
$$;

create or replace function public.catalyst_consent_interested(
  p_event_id text, p_limit integer
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare v_out jsonb;
begin
  if p_event_id is null or p_event_id !~ '^[A-Za-z0-9_.:-]{1,128}$'
     or p_limit is null or p_limit not between 1 and 100 then
    raise exception 'CONSENT_INTEREST_QUERY_INVALID';
  end if;
  select coalesce(pg_catalog.jsonb_agg(e.record), '[]'::jsonb)
   into v_out from (
     select pg_catalog.jsonb_build_object(
       'user_id',g.user_id,'email',pg_catalog.lower(pg_catalog.btrim(u.email)),
       'event_id',g.event_id,'scope',g.scope,'tickers',pg_catalog.to_jsonb(g.tickers),
       'intent_id',g.intent_id,'verified_at_utc',g.verified_at_utc,
       'first_touch',g.first_touch,'revoked_at_utc',g.revoked_at_utc
     ) as record
     from public.catalyst_consent_grants g join auth.users u on u.id=g.user_id
     where g.event_id=p_event_id and g.scope='catalyst_event_updates/v1'
       and g.revoked_at_utc is null and u.email_confirmed_at is not null
       and not exists (select 1 from public.email_suppression s
                        where pg_catalog.lower(pg_catalog.btrim(s.email))
                            = pg_catalog.lower(pg_catalog.btrim(u.email)))
       and not exists (select 1 from public.email_prefs p
                        where p.user_id=g.user_id and p.marketing_opt_out)
     order by g.verified_at_utc asc, g.user_id asc
     limit p_limit
   ) e;
  return v_out;
end;
$$;

create or replace function public.catalyst_consent_revoke(
  p_user_id uuid, p_event_id text, p_revoked_at_utc text
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare v_at timestamptz; v_changed integer;
begin
  if p_user_id is null or p_event_id is null or p_revoked_at_utc is null then
    raise exception 'CONSENT_REVOKE_INVALID';
  end if;
  begin v_at := p_revoked_at_utc::timestamptz;
  exception when others then raise exception 'CONSENT_REVOKE_TIME_INVALID'; end;
  if v_at is null or v_at > pg_catalog.now() + interval '30 seconds'
     or v_at < pg_catalog.now() - interval '5 minutes' then
    raise exception 'CONSENT_REVOKE_TIME_INVALID';
  end if;
  update public.catalyst_consent_grants g set revoked_at_utc=v_at
    where g.user_id=p_user_id and g.event_id=p_event_id
      and g.scope='catalyst_event_updates/v1'
      and g.revoked_at_utc is null;
  get diagnostics v_changed = row_count;
  return pg_catalog.jsonb_build_object('changed',v_changed=1);
end;
$$;

-- Incumbent email-estate mutations are the only global unsubscribe owner.
-- Revocation is permanent for Catalyst positive scopes: removing a general
-- email suppression or clearing email_prefs does NOT resurrect an event grant.
-- Lock keys match catalyst_consent_confirm's fixed order (see header).
create or replace function public.catalyst_consent_on_global_address_suppression()
returns trigger language plpgsql security definer set search_path = ''
as $catalyst_address_revocation$
declare v_email text;
begin
  v_email := pg_catalog.lower(pg_catalog.btrim(new.email));
  if v_email is null or v_email = '' then
    -- Never block an incumbent write: the suppression table's own constraints own
    -- address validity. Nothing to revoke for a blank address.
    return new;
  end if;
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('mmx-catalyst-email:' || v_email, 24001));
  update public.catalyst_consent_grants g
     set revoked_at_utc = pg_catalog.now()
    from auth.users u
   where g.user_id = u.id
     and pg_catalog.lower(pg_catalog.btrim(u.email)) = v_email
     and g.revoked_at_utc is null;
  return new;
end;
$catalyst_address_revocation$;
revoke all on function public.catalyst_consent_on_global_address_suppression()
  from public, anon, authenticated, service_role;
drop trigger if exists catalyst_consent_global_address_revocation
  on public.email_suppression;
create trigger catalyst_consent_global_address_revocation
  before insert or update of email, reason on public.email_suppression
  for each row execute function public.catalyst_consent_on_global_address_suppression();

create or replace function public.catalyst_consent_on_global_user_optout()
returns trigger language plpgsql security definer set search_path = ''
as $catalyst_user_revocation$
begin
  if new.marketing_opt_out is true then
    perform pg_catalog.pg_advisory_xact_lock(
      pg_catalog.hashtextextended('mmx-catalyst-user:' || new.user_id::text, 24001));
    update public.catalyst_consent_grants g
       set revoked_at_utc = pg_catalog.now()
     where g.user_id = new.user_id
       and g.revoked_at_utc is null;
  end if;
  return new;
end;
$catalyst_user_revocation$;
revoke all on function public.catalyst_consent_on_global_user_optout()
  from public, anon, authenticated, service_role;
drop trigger if exists catalyst_consent_global_user_revocation
  on public.email_prefs;
create trigger catalyst_consent_global_user_revocation
  before insert or update of marketing_opt_out on public.email_prefs
  for each row execute function public.catalyst_consent_on_global_user_optout();

-- Re-apply reconciliation (see header): revoke, idempotently, every active grant whose
-- user is opted out or whose address is suppressed. The grant guard permits exactly
-- this transition (NULL -> revoked). No-op on a clean first apply.
update public.catalyst_consent_grants g
   set revoked_at_utc = pg_catalog.now()
  from auth.users u
 where g.user_id = u.id
   and g.revoked_at_utc is null
   and (exists (select 1 from public.email_prefs e
                 where e.user_id = g.user_id and e.marketing_opt_out)
        or exists (select 1 from public.email_suppression s
                    where pg_catalog.lower(pg_catalog.btrim(s.email))
                        = pg_catalog.lower(pg_catalog.btrim(u.email))));

-- All seven entrypoints accept only private service-role PostgREST callers.
-- SECURITY DEFINER does not make them public RPCs. No browser role can EXECUTE.
revoke all on function public.catalyst_consent_contract() from public, anon, authenticated;
revoke all on function public.catalyst_consent_begin(text,text,text) from public, anon, authenticated;
revoke all on function public.catalyst_consent_resolve(text,text) from public, anon, authenticated;
revoke all on function public.catalyst_consent_confirm(uuid,text,text,text[],text,text,jsonb) from public, anon, authenticated;
revoke all on function public.catalyst_consent_current(uuid,text) from public, anon, authenticated;
revoke all on function public.catalyst_consent_interested(text,integer) from public, anon, authenticated;
revoke all on function public.catalyst_consent_revoke(uuid,text,text) from public, anon, authenticated;
grant execute on function public.catalyst_consent_contract() to service_role;
grant execute on function public.catalyst_consent_begin(text,text,text) to service_role;
grant execute on function public.catalyst_consent_resolve(text,text) to service_role;
grant execute on function public.catalyst_consent_confirm(uuid,text,text,text[],text,text,jsonb) to service_role;
grant execute on function public.catalyst_consent_current(uuid,text) to service_role;
grant execute on function public.catalyst_consent_interested(text,integer) to service_role;
grant execute on function public.catalyst_consent_revoke(uuid,text,text) to service_role;

-- Final install fence: existing policies, client grants, a service_role table grant,
-- a foreign owner, FORCE RLS or an incumbent table the owner cannot read are a STOP,
-- never silently accepted by CREATE TABLE
-- IF NOT EXISTS or the RPC grant phase. A fence failure rolls the whole file back.
do $consent_install_fence$
declare
  v_fn text;
  v_tbl text;
  v_priv text;
  v_table_owner oid;
  v_owner_name text;
  v_pending_owner oid;
  v_bypass boolean;
  v_rec record;
begin
  if exists (
    select 1 from pg_catalog.pg_policies p
    where p.schemaname='public' and p.tablename in
      ('catalyst_consent_pending','catalyst_consent_grants')
  ) then
    raise exception 'CATALYST_CONSENT_EXISTING_CLIENT_POLICY_BLOCK';
  end if;
  foreach v_tbl in array array['public.catalyst_consent_pending','public.catalyst_consent_grants'] loop
    foreach v_priv in array array['SELECT','INSERT','UPDATE','DELETE'] loop
      if pg_catalog.has_table_privilege('anon', v_tbl, v_priv)
         or pg_catalog.has_table_privilege('authenticated', v_tbl, v_priv)
         or pg_catalog.has_table_privilege('service_role', v_tbl, v_priv) then
        raise exception 'CATALYST_CONSENT_CLIENT_TABLE_GRANT_BLOCK: % %', v_tbl, v_priv;
      end if;
    end loop;
  end loop;
  if pg_catalog.has_sequence_privilege('anon','public.catalyst_consent_grants_grant_id_seq','USAGE')
     or pg_catalog.has_sequence_privilege('authenticated','public.catalyst_consent_grants_grant_id_seq','USAGE')
     or pg_catalog.has_sequence_privilege('service_role','public.catalyst_consent_grants_grant_id_seq','USAGE') then
    raise exception 'CATALYST_CONSENT_CLIENT_SEQUENCE_GRANT_BLOCK';
  end if;
  if exists (
    select 1 from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname in ('catalyst_consent_pending','catalyst_consent_grants')
      and (c.relforcerowsecurity or not c.relrowsecurity)
  ) then
    raise exception 'CATALYST_CONSENT_RLS_MODE_BLOCK';
  end if;
  select c.relowner into v_table_owner
    from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname='catalyst_consent_grants';
  select r.rolname into v_owner_name from pg_catalog.pg_roles r where r.oid=v_table_owner;
  if v_owner_name is null or v_owner_name in ('anon','authenticated','service_role') then
    raise exception 'CATALYST_CONSENT_TABLE_OWNER_BLOCK';
  end if;
  select c.relowner into v_pending_owner
    from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
   where n.nspname='public' and c.relname='catalyst_consent_pending';
  if v_pending_owner is distinct from v_table_owner then
    raise exception 'CATALYST_CONSENT_TABLE_OWNER_BLOCK: pending';
  end if;
  -- The SECURITY DEFINER bodies read the incumbent email tables as the owner: it must
  -- own them (or hold BYPASSRLS) and they must not be FORCE RLS, or the suppression
  -- veto and the interested() filter would silently see no rows.
  if (select pg_catalog.count(*) from pg_catalog.pg_class c
        join pg_catalog.pg_namespace n on n.oid=c.relnamespace
       where n.nspname='public' and c.relname in ('email_suppression','email_prefs')) <> 2 then
    raise exception 'CATALYST_CONSENT_INCUMBENT_TABLE_MISSING_BLOCK';
  end if;
  select r.rolbypassrls into v_bypass from pg_catalog.pg_roles r where r.oid=v_table_owner;
  for v_rec in
    select c.relname, c.relowner, c.relforcerowsecurity
      from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
     where n.nspname='public' and c.relname in ('email_suppression','email_prefs')
  loop
    if not coalesce(v_bypass,false)
       and (v_rec.relowner is distinct from v_table_owner or v_rec.relforcerowsecurity) then
      raise exception 'CATALYST_CONSENT_INCUMBENT_TABLE_ACCESS_BLOCK: %', v_rec.relname;
    end if;
  end loop;
  if not pg_catalog.has_table_privilege(v_owner_name, 'auth.users', 'SELECT') then
    raise exception 'CATALYST_CONSENT_AUTH_USERS_READ_BLOCK';
  end if;
  foreach v_fn in array array[
    'catalyst_consent_contract()',
    'catalyst_consent_begin(text,text,text)',
    'catalyst_consent_resolve(text,text)',
    'catalyst_consent_confirm(uuid,text,text,text[],text,text,jsonb)',
    'catalyst_consent_current(uuid,text)',
    'catalyst_consent_interested(text,integer)',
    'catalyst_consent_revoke(uuid,text,text)'
  ] loop
    if pg_catalog.has_function_privilege('anon', 'public.'||v_fn, 'EXECUTE')
       or pg_catalog.has_function_privilege('authenticated','public.'||v_fn,'EXECUTE')
       or not pg_catalog.has_function_privilege('service_role','public.'||v_fn,'EXECUTE')
    then
      raise exception 'CATALYST_CONSENT_RPC_PRIVILEGE_BLOCK: %',v_fn;
    end if;
    if (select p.proowner from pg_catalog.pg_proc p
         where p.oid = ('public.'||v_fn)::regprocedure) is distinct from v_table_owner then
      raise exception 'CATALYST_CONSENT_RPC_OWNER_BLOCK: %',v_fn;
    end if;
  end loop;
  foreach v_fn in array array[
    'catalyst_consent_grant_guard()',
    'catalyst_consent_on_global_address_suppression()',
    'catalyst_consent_on_global_user_optout()'
  ] loop
    if (select p.proowner from pg_catalog.pg_proc p
         where p.oid = ('public.'||v_fn)::regprocedure) is distinct from v_table_owner then
      raise exception 'CATALYST_CONSENT_TRIGGER_OWNER_BLOCK: %',v_fn;
    end if;
  end loop;
end;
$consent_install_fence$;

commit;
