-- Portfolio digest consent: extend the existing email_prefs owner.
-- Source candidate only. Apply through the reviewed migration route before enrollment.
-- Every disable advances the server revision; enables compare the user's observed
-- revision. No SMTP, delivery identity, consent mirror or retry queue is introduced.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $preflight$
DECLARE owner_id oid; guard_id oid; uid_att smallint; choice_att smallint; revision_att smallint;
BEGIN
  IF to_regclass('public.email_prefs') IS NULL THEN
    RAISE EXCEPTION 'email_prefs prerequisite missing';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='macro_digest_consent_owner') THEN
    CREATE ROLE macro_digest_consent_owner NOLOGIN NOINHERIT NOSUPERUSER
      NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  SELECT oid INTO owner_id FROM pg_roles WHERE rolname='macro_digest_consent_owner'
    AND NOT (rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole
             OR rolreplication OR rolbypassrls);
  IF owner_id IS NULL OR EXISTS (
    SELECT 1 FROM pg_auth_members WHERE roleid=owner_id OR member=owner_id
  ) THEN RAISE EXCEPTION 'digest owner identity or membership mismatch'; END IF;
  guard_id := to_regprocedure('public.portfolio_digest_consent_guard_v1()');
  IF EXISTS (SELECT 1 FROM pg_attribute
      WHERE attrelid='public.email_prefs'::regclass
        AND attname IN ('portfolio_digest_opt_in','portfolio_digest_revision')
        AND NOT attisdropped)
    AND (guard_id IS NULL OR NOT EXISTS (
      SELECT 1 FROM pg_proc WHERE oid=guard_id AND proowner=owner_id AND NOT prosecdef
    )) THEN
    RAISE EXCEPTION 'pre-existing digest columns lack the guarded owner contract';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='public.email_prefs'::regclass
      AND NOT tgisinternal AND (guard_id IS NULL OR tgfoid<>guard_id OR tgname NOT IN (
        'portfolio_digest_consent_insert_v1','portfolio_digest_consent_update_v1',
        'portfolio_digest_consent_identity_v1')))
    OR EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.email_prefs'::regclass
      AND polname<>'portfolio_digest_consent_owner_v1')
  THEN RAISE EXCEPTION 'unqualified email_prefs trigger or policy'; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_class WHERE oid='public.email_prefs'::regclass AND relrowsecurity)
  THEN RAISE EXCEPTION 'email_prefs RLS prerequisite missing'; END IF;
  IF guard_id IS NOT NULL THEN
    SELECT attnum INTO uid_att FROM pg_attribute WHERE attrelid='public.email_prefs'::regclass
      AND attname='user_id' AND NOT attisdropped;
    SELECT attnum INTO choice_att FROM pg_attribute WHERE attrelid='public.email_prefs'::regclass
      AND attname='portfolio_digest_opt_in' AND NOT attisdropped;
    SELECT attnum INTO revision_att FROM pg_attribute WHERE attrelid='public.email_prefs'::regclass
      AND attname='portfolio_digest_revision' AND NOT attisdropped;
    IF (SELECT count(*) FROM pg_trigger t WHERE tgrelid='public.email_prefs'::regclass
        AND NOT tgisinternal AND tgfoid=guard_id AND tgenabled='O' AND (
          (tgname='portfolio_digest_consent_insert_v1' AND tgtype=7 AND tgnargs=0) OR
          (tgname='portfolio_digest_consent_update_v1' AND tgtype=19 AND tgnargs=0
            AND cardinality(tgattr::smallint[])=2
            AND tgattr::smallint[] @> ARRAY[choice_att,revision_att]) OR
          (tgname='portfolio_digest_consent_identity_v1' AND tgtype=19 AND tgnargs=1
            AND cardinality(tgattr::smallint[])=1 AND tgattr::smallint[] @> ARRAY[uid_att]
            AND tgargs=decode('6964656e7469747900','hex'))
        )) <> 3
      OR NOT EXISTS (SELECT 1 FROM pg_policy WHERE polrelid='public.email_prefs'::regclass
        AND polname='portfolio_digest_consent_owner_v1' AND polroles=ARRAY[owner_id]
        AND polcmd='*' AND polpermissive
        AND pg_get_expr(polqual,polrelid)='true' AND pg_get_expr(polwithcheck,polrelid)='true')
      OR has_schema_privilege(owner_id,'public','CREATE')
    THEN RAISE EXCEPTION 'digest guard, policy or owner authority drift'; END IF;
    IF has_table_privilege('service_role','public.email_prefs','DELETE,TRUNCATE')
      OR has_table_privilege('anon','public.email_prefs','DELETE,TRUNCATE')
      OR has_table_privilege('authenticated','public.email_prefs','DELETE,TRUNCATE')
    THEN RAISE EXCEPTION 'application erasure privilege drift'; END IF;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class WHERE relowner=owner_id)
    OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner=owner_id)
    OR EXISTS (SELECT 1 FROM pg_proc WHERE proowner=owner_id AND oid NOT IN (
      COALESCE(guard_id,0),
      COALESCE(to_regprocedure('public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)')::oid,0)
    ))
    OR EXISTS (SELECT 1 FROM pg_proc WHERE oid IN (
      COALESCE(guard_id,0),
      COALESCE(to_regprocedure('public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)')::oid,0)
    ) AND proowner<>owner_id)
  THEN RAISE EXCEPTION 'digest owner function or object ownership mismatch'; END IF;
END
$preflight$;

ALTER TABLE public.email_prefs
  ADD COLUMN IF NOT EXISTS portfolio_digest_opt_in boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS portfolio_digest_revision uuid NOT NULL DEFAULT gen_random_uuid();

DO $shape$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.email_prefs'::regclass
      AND attname='portfolio_digest_opt_in' AND atttypid='boolean'::regtype AND attnotnull)
    OR NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.email_prefs'::regclass
      AND attname='portfolio_digest_revision' AND atttypid='uuid'::regtype AND attnotnull)
    OR NOT EXISTS (SELECT 1 FROM pg_attrdef d JOIN pg_attribute a
        ON a.attrelid=d.adrelid AND a.attnum=d.adnum
        WHERE a.attrelid='public.email_prefs'::regclass AND a.attname='portfolio_digest_opt_in'
          AND pg_get_expr(d.adbin,d.adrelid)='false')
    OR NOT EXISTS (SELECT 1 FROM pg_attrdef d JOIN pg_attribute a
        ON a.attrelid=d.adrelid AND a.attnum=d.adnum
        WHERE a.attrelid='public.email_prefs'::regclass AND a.attname='portfolio_digest_revision'
          AND pg_get_expr(d.adbin,d.adrelid) IN ('gen_random_uuid()','pg_catalog.gen_random_uuid()'))
  THEN RAISE EXCEPTION 'digest column shape or default mismatch'; END IF;
END
$shape$;

-- Erasing a row would restore "absent" and invalidate a withdrawal tombstone.
-- Supported application writers cannot erase it. The Auth FK cascade is retained;
-- database-owner maintenance/reused account UUIDs remain a separate authority boundary.
REVOKE DELETE,TRUNCATE ON public.email_prefs FROM PUBLIC,anon,authenticated,service_role;

GRANT USAGE ON SCHEMA public TO macro_digest_consent_owner;
GRANT SELECT (user_id,portfolio_digest_opt_in,portfolio_digest_revision,marketing_opt_out)
  ON public.email_prefs TO macro_digest_consent_owner;
GRANT INSERT (user_id,portfolio_digest_opt_in,portfolio_digest_revision)
  ON public.email_prefs TO macro_digest_consent_owner;
GRANT UPDATE (portfolio_digest_opt_in,portfolio_digest_revision,updated_at)
  ON public.email_prefs TO macro_digest_consent_owner;
ALTER TABLE public.email_prefs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS portfolio_digest_consent_owner_v1 ON public.email_prefs;
CREATE POLICY portfolio_digest_consent_owner_v1 ON public.email_prefs
  TO macro_digest_consent_owner USING (true) WITH CHECK (true);

-- The role is not assumable by application sessions. The trigger is INVOKER so
-- current_user denotes the actual writer, not the trigger function's owner.
CREATE OR REPLACE FUNCTION public.portfolio_digest_consent_guard_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,pg_temp AS $guard$
BEGIN
  IF TG_NARGS=1 AND TG_ARGV[0]='identity' THEN
    IF NEW.user_id IS DISTINCT FROM OLD.user_id THEN
      RAISE EXCEPTION 'email preference account identity is immutable' USING ERRCODE='42501';
    END IF;
    RETURN NEW;
  END IF;
  IF current_user <> 'macro_digest_consent_owner' THEN
    IF NEW.portfolio_digest_opt_in IS DISTINCT FROM false THEN
      RAISE EXCEPTION 'positive digest consent requires the guarded RPC'
        USING ERRCODE='42501';
    END IF;
    NEW.portfolio_digest_opt_in := false;
    NEW.portfolio_digest_revision := gen_random_uuid();
  END IF;
  RETURN NEW;
END
$guard$;

-- Preserve language/global opt-out partial updates: neither names these columns.
-- A legacy digest-negative write, including false->false, is a real withdrawal.
DROP TRIGGER IF EXISTS portfolio_digest_consent_insert_v1 ON public.email_prefs;
CREATE TRIGGER portfolio_digest_consent_insert_v1 BEFORE INSERT ON public.email_prefs
  FOR EACH ROW EXECUTE FUNCTION public.portfolio_digest_consent_guard_v1();
DROP TRIGGER IF EXISTS portfolio_digest_consent_update_v1 ON public.email_prefs;
CREATE TRIGGER portfolio_digest_consent_update_v1
  BEFORE UPDATE OF portfolio_digest_opt_in,portfolio_digest_revision ON public.email_prefs
  FOR EACH ROW EXECUTE FUNCTION public.portfolio_digest_consent_guard_v1();

-- Separate identity guard: same-user partial upserts may include user_id in SET
-- without representing a digest decision or advancing its revision.
DROP TRIGGER IF EXISTS portfolio_digest_consent_identity_v1 ON public.email_prefs;
CREATE TRIGGER portfolio_digest_consent_identity_v1
  BEFORE UPDATE OF user_id ON public.email_prefs
  FOR EACH ROW EXECUTE FUNCTION public.portfolio_digest_consent_guard_v1('identity');

CREATE OR REPLACE FUNCTION public.portfolio_digest_consent_set_v1(
  p_user_id uuid, p_enabled boolean, p_expected_revision uuid DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $set$
DECLARE
  changed boolean;
  result_uid uuid;
  result_enabled boolean;
  result_revision uuid;
  result_marketing_opt_out boolean;
BEGIN
  IF p_user_id IS NULL OR p_enabled IS NULL THEN
    RAISE EXCEPTION 'digest user and decision are required' USING ERRCODE='22023';
  END IF;
  IF NOT p_enabled THEN
    INSERT INTO public.email_prefs AS p
      (user_id,portfolio_digest_opt_in,portfolio_digest_revision)
      VALUES (p_user_id,false,gen_random_uuid())
      ON CONFLICT (user_id) DO UPDATE SET
        portfolio_digest_opt_in=false,portfolio_digest_revision=gen_random_uuid(),
        updated_at=clock_timestamp()
      RETURNING p.user_id,p.portfolio_digest_opt_in,p.portfolio_digest_revision,
                p.marketing_opt_out
      INTO result_uid,result_enabled,result_revision,result_marketing_opt_out;
  ELSIF p_expected_revision IS NULL THEN
    -- NULL means the explicit client observation was "no preference row".
    INSERT INTO public.email_prefs AS p
      (user_id,portfolio_digest_opt_in,portfolio_digest_revision)
      VALUES (p_user_id,true,gen_random_uuid())
      ON CONFLICT (user_id) DO NOTHING
      RETURNING p.user_id,p.portfolio_digest_opt_in,p.portfolio_digest_revision,
                p.marketing_opt_out
      INTO result_uid,result_enabled,result_revision,result_marketing_opt_out;
  ELSE
    UPDATE public.email_prefs AS p SET portfolio_digest_opt_in=true,
      portfolio_digest_revision=gen_random_uuid(),updated_at=clock_timestamp()
      WHERE p.user_id=p_user_id AND p.portfolio_digest_revision=p_expected_revision
      RETURNING p.user_id,p.portfolio_digest_opt_in,p.portfolio_digest_revision,
                p.marketing_opt_out
      INTO result_uid,result_enabled,result_revision,result_marketing_opt_out;
  END IF;
  changed := FOUND;
  IF NOT changed THEN
    SELECT p.user_id,p.portfolio_digest_opt_in,p.portfolio_digest_revision,p.marketing_opt_out
      INTO result_uid,result_enabled,result_revision,result_marketing_opt_out
      FROM public.email_prefs AS p WHERE p.user_id=p_user_id;
  END IF;
  RETURN jsonb_build_object(
    'status', CASE WHEN changed THEN 'applied' ELSE 'stale_revision' END,
    'state', CASE WHEN result_uid IS NULL THEN NULL ELSE jsonb_build_object(
      'user_id',result_uid,'portfolio_digest_opt_in',result_enabled,
      'portfolio_digest_revision',result_revision,'marketing_opt_out',result_marketing_opt_out
    ) END);
END
$set$;

-- ALTER OWNER requires CREATE for the new owner; remove it in this transaction.
GRANT CREATE ON SCHEMA public TO macro_digest_consent_owner;
ALTER FUNCTION public.portfolio_digest_consent_guard_v1() OWNER TO macro_digest_consent_owner;
ALTER FUNCTION public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)
  OWNER TO macro_digest_consent_owner;
REVOKE CREATE ON SCHEMA public FROM macro_digest_consent_owner;
REVOKE ALL ON FUNCTION public.portfolio_digest_consent_guard_v1()
  FROM PUBLIC,anon,authenticated,service_role;
REVOKE ALL ON FUNCTION public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)
  FROM PUBLIC,anon,authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)
  TO service_role;

DO $effective_authority$
DECLARE owner_id oid; service_id oid;
BEGIN
  SELECT oid INTO owner_id FROM pg_roles WHERE rolname='macro_digest_consent_owner';
  SELECT oid INTO service_id FROM pg_roles WHERE rolname='service_role';
  IF has_table_privilege(owner_id,'public.email_prefs','SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
    OR has_schema_privilege(owner_id,'public','CREATE')
    OR has_column_privilege(owner_id,'public.email_prefs','lang','SELECT,INSERT,UPDATE')
    OR has_column_privilege(owner_id,'public.email_prefs','marketing_opt_out','INSERT,UPDATE')
    OR has_column_privilege(owner_id,'public.email_prefs','user_id','UPDATE')
    OR has_table_privilege('service_role','public.email_prefs','DELETE,TRUNCATE')
    OR has_table_privilege('anon','public.email_prefs','DELETE,TRUNCATE')
    OR has_table_privilege('authenticated','public.email_prefs','DELETE,TRUNCATE')
    OR EXISTS (SELECT 1 FROM pg_proc p,
      LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
      WHERE p.oid='public.portfolio_digest_consent_guard_v1()'::regprocedure
        AND a.privilege_type='EXECUTE' AND a.grantee<>owner_id)
    OR EXISTS (SELECT 1 FROM pg_proc p,
      LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
      WHERE p.oid='public.portfolio_digest_consent_set_v1(uuid,boolean,uuid)'::regprocedure
        AND a.privilege_type='EXECUTE' AND a.grantee NOT IN (owner_id,service_id))
  THEN RAISE EXCEPTION 'digest effective authority is broader than the contract'; END IF;
END
$effective_authority$;
COMMIT;
