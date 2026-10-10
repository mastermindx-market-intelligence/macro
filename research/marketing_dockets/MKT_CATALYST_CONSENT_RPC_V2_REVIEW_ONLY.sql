-- REVIEW ONLY / NOT APPLIED. CATALYST POSITIVE EVENT CONSENT v2.
-- Proposed extension of the incumbent Supabase email estate (0007_support_email.sql).
-- OWNER: existing email/consent/SQL owner. This file is NOT an automatic migration.
-- DO NOT run on production without the incumbent owner's security review,
-- staging transaction/role proof, rollout authority, rollback and separate approval.
-- Admits no new auth, sender, public queue, license, or marketing-opt-in inference.
--
-- RPCs match app.catalyst_optin.SupabaseConsentRpcOwner v2 exactly.
-- Critical trust: only service_role can invoke these functions. The application
-- validates the signed HMAC intent and GoTrue OTP; the database locks the exact
-- pending intent attributes and requires the EXISTING auth.users confirmed ID.
-- The SQL parses HMAC payload fields for binding but DOES NOT forge/verify HMAC.
-- A cryptographic signature is checked only in the incumbent application.
--
-- SQL owner must verify pg_catalog gen_random_uuid, actual auth.users layout,
-- existing mailer email_prefs/email_suppression, RLS and PostgREST RPC behavior.

begin;

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

-- These are private owner data, never an unrestricted REST surface.
revoke all on public.catalyst_consent_pending from public, anon, authenticated;
revoke all on public.catalyst_consent_grants from public, anon, authenticated;
revoke all on sequence public.catalyst_consent_grants_grant_id_seq
  from public, anon, authenticated;
-- Existing installation must keep RLS with zero client policies.
-- No anonymous/authenticated policy is created or relaxed here.

create or replace function public.catalyst_consent_contract()
returns jsonb language sql security definer set search_path = ''
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
  if p_intent is null or pg_catalog.length(p_intent) not between 80 and 4096
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
  if pg_catalog.jsonb_typeof(v_payload) <> 'object'
     or v_payload->>'v' <> '1'
     or v_scope <> 'catalyst_event_updates/v1'
     or v_nonce !~ '^[A-Za-z0-9_-]{20,96}$'
     or v_event !~ '^[A-Za-z0-9_.:-]{1,128}$'
     or v_payload->>'email_tag' <> p_email_tag
     or pg_catalog.jsonb_typeof(v_payload->'tickers') <> 'array'
     or pg_catalog.jsonb_typeof(v_touch) <> 'object'
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
  if pg_catalog.cardinality(v_tickers) not between 1 and 10
     or (select pg_catalog.count(distinct t) from pg_catalog.unnest(v_tickers) as t)
        <> pg_catalog.cardinality(v_tickers)
     or exists (select 1 from pg_catalog.unnest(v_tickers) t
                where t !~ '^[A-Z][A-Z0-9.-]{0,9}$')
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

  -- 256-bit CSPRNG opaque handle derived from two independent built-in v4 UUIDs.
  v_ref := pg_catalog.replace(pg_catalog.gen_random_uuid()::text,'-','') ||
           pg_catalog.replace(pg_catalog.gen_random_uuid()::text,'-','');
  insert into public.catalyst_consent_pending
      (public_ref,signed_intent,email_tag,intent_id,event_id,scope,
       tickers,first_touch,expires_at_utc)
  values (v_ref,p_intent,p_email_tag,v_nonce,v_event,v_scope,
          v_tickers,v_touch,v_expires);
  return pg_catalog.jsonb_build_object('public_ref',v_ref);
end;
$$;

create or replace function public.catalyst_consent_resolve(
  p_public_ref text, p_email_tag text
) returns jsonb language plpgsql security definer set search_path = ''
as $$
declare v_intent text;
begin
  if p_public_ref !~ '^[A-Za-z0-9_-]{8,128}$'
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
begin
  if p_scope <> 'catalyst_event_updates/v1' or p_intent_id is null
     or p_intent_id !~ '^[A-Za-z0-9_-]{20,96}$' then
    raise exception 'CONSENT_PURPOSE_INVALID';
  end if;
  select * into v_pending
    from public.catalyst_consent_pending p
   where p.intent_id=p_intent_id and p.expires_at_utc > pg_catalog.now()
   for update;
  if not found then raise exception 'CONSENT_PENDING_NOT_CURRENT'; end if;
  if v_pending.event_id is distinct from p_event_id
     or v_pending.scope is distinct from p_scope
     or v_pending.tickers is distinct from p_tickers
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
  if v_email is null or v_confirmed is null
     or v_confirmed > v_verified + interval '30 seconds' then
    raise exception 'CONSENT_GOTRUE_UNVERIFIED';
  end if;
  -- Acquire the SAME fixed-order transaction locks as incumbent global
  -- unsubscribe and preference-update triggers BEFORE inspecting suppression
  -- and before INSERT. Prevent READ COMMITTED check-then-insert write skew.
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('mmx-catalyst-email:' || v_email, 24001));
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended('mmx-catalyst-user:' || p_user_id::text, 24001));
  -- Mandatory additional current suppression veto, not an opt-in inference.
  if exists (select 1 from public.email_suppression s
              where pg_catalog.lower(s.email) = v_email)
     or exists (select 1 from public.email_prefs e
                 where e.user_id=p_user_id and e.marketing_opt_out) then
    raise exception 'CONSENT_ADDRESS_SUPPRESSED';
  end if;

  insert into public.catalyst_consent_grants
    (user_id,event_id,scope,tickers,intent_id,verified_at_utc,first_touch)
  values (p_user_id,p_event_id,p_scope,p_tickers,p_intent_id,v_verified,p_first_touch)
  on conflict (user_id,event_id,scope) do nothing
  returning * into v_record;
  if found then
    v_created := true;
  else
    select * into v_record from public.catalyst_consent_grants g
     where g.user_id=p_user_id and g.event_id=p_event_id and g.scope=p_scope;
  end if;
  if v_record.grant_id is null or v_record.revoked_at_utc is not null
     or v_record.tickers is distinct from p_tickers then
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
  if p_event_id !~ '^[A-Za-z0-9_.:-]{1,128}$'
     or p_limit not between 1 and 100 then
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
                        where pg_catalog.lower(s.email) = pg_catalog.lower(u.email))
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
-- Revocation is permanent for old Catalyst positive scopes: removing a general
-- email suppression or clearing email_prefs does NOT resurrect an event grant.
-- Trigger lock keys match catalyst_consent_confirm's fixed lock order.
create or replace function public.catalyst_consent_on_global_address_suppression()
returns trigger language plpgsql security definer set search_path = ''
as $
declare v_email text;
begin
  v_email := pg_catalog.lower(pg_catalog.btrim(new.email));
  if v_email is null or v_email = '' then
    raise exception 'CATALYST_SUPPRESSION_ADDRESS_INVALID';
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
$;
revoke all on function public.catalyst_consent_on_global_address_suppression()
  from public, anon, authenticated;
drop trigger if exists catalyst_consent_global_address_revocation
  on public.email_suppression;
create trigger catalyst_consent_global_address_revocation
  before insert or update of email, reason on public.email_suppression
  for each row execute function public.catalyst_consent_on_global_address_suppression();

create or replace function public.catalyst_consent_on_global_user_optout()
returns trigger language plpgsql security definer set search_path = ''
as $
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
$;
revoke all on function public.catalyst_consent_on_global_user_optout()
  from public, anon, authenticated;
drop trigger if exists catalyst_consent_global_user_revocation
  on public.email_prefs;
create trigger catalyst_consent_global_user_revocation
  before insert or update of marketing_opt_out on public.email_prefs
  for each row execute function public.catalyst_consent_on_global_user_optout();

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

-- Final install fence: existing policies or client grants are a STOP, never
-- silently accepted by CREATE TABLE IF NOT EXISTS or the RPC grant phase.
do $consent_install_fence$
declare v_fn text;
begin
  if exists (
    select 1 from pg_catalog.pg_policies p
    where p.schemaname='public' and p.tablename in
      ('catalyst_consent_pending','catalyst_consent_grants')
  ) then
    raise exception 'CATALYST_CONSENT_EXISTING_CLIENT_POLICY_BLOCK';
  end if;
  if pg_catalog.has_table_privilege('anon','public.catalyst_consent_pending','SELECT')
     or pg_catalog.has_table_privilege('authenticated','public.catalyst_consent_pending','SELECT')
     or pg_catalog.has_table_privilege('anon','public.catalyst_consent_grants','SELECT')
     or pg_catalog.has_table_privilege('authenticated','public.catalyst_consent_grants','SELECT')
  then
    raise exception 'CATALYST_CONSENT_CLIENT_TABLE_GRANT_BLOCK';
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
  end loop;
end;
$consent_install_fence$;

commit;
