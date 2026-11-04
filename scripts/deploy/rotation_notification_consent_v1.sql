-- Rotation notification consent C0, source-only migration candidate.
-- Existing auth.users remains the identity/preferences owner. No roster, outbox,
-- scheduler, sender or activation flag is created. Production compatibility,
-- independent review and the account-route integration are separate gates.
BEGIN;
DO $admit$
BEGIN
  IF current_setting('server_version_num')::integer < 130000 THEN
    RAISE EXCEPTION 'rotation consent requires PostgreSQL 13 or newer';
  END IF;
  IF to_regclass('auth.users') IS NULL
     OR NOT EXISTS (SELECT FROM pg_roles WHERE rolname='service_role')
     OR NOT EXISTS (SELECT FROM pg_roles WHERE rolname='supabase_auth_admin')
     OR NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon')
     OR NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') THEN
    RAISE EXCEPTION 'rotation consent incumbent Auth roles/table missing';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname='macro_rotation_consent_owner') THEN
    IF NOT EXISTS (
      SELECT FROM pg_roles
      WHERE rolname='macro_rotation_consent_owner'
        AND NOT rolcanlogin AND NOT rolsuper AND NOT rolinherit
        AND NOT rolcreatedb AND NOT rolcreaterole AND NOT rolreplication
        AND NOT rolbypassrls
        AND shobj_description(oid,'pg_authid')='Macro rotation consent C0 owner v1'
    ) OR EXISTS (
      SELECT FROM pg_auth_members m JOIN pg_roles r
      ON r.oid=m.roleid OR r.oid=m.member
      WHERE r.rolname='macro_rotation_consent_owner'
    ) THEN
      RAISE EXCEPTION 'rotation consent owner identity or membership mismatch';
    END IF;
  ELSE
    CREATE ROLE macro_rotation_consent_owner NOLOGIN NOINHERIT NOSUPERUSER
      NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    COMMENT ON ROLE macro_rotation_consent_owner IS 'Macro rotation consent C0 owner v1';
  END IF;
  IF EXISTS (
    SELECT FROM pg_proc p WHERE p.proowner=(SELECT oid FROM pg_roles
      WHERE rolname='macro_rotation_consent_owner')
    AND NOT EXISTS (SELECT FROM unnest(ARRAY[
      'auth.mmx_rotation_prefs_allow_v1(jsonb)',
      'auth.mmx_rotation_marker_valid_v1(jsonb)',
      'auth.mmx_rotation_state_v1(uuid,jsonb,jsonb)',
      'auth.mmx_rotation_consent_guard_v1()',
      'public.rotation_consent_read_v1(uuid)',
      'public.rotation_consent_set_v1(uuid,boolean,uuid)'
    ]) AS allowed(signature) WHERE p.oid=to_regprocedure(allowed.signature))
  ) OR EXISTS (
    SELECT FROM unnest(ARRAY[
      'auth.mmx_rotation_prefs_allow_v1(jsonb)',
      'auth.mmx_rotation_marker_valid_v1(jsonb)',
      'auth.mmx_rotation_state_v1(uuid,jsonb,jsonb)',
      'auth.mmx_rotation_consent_guard_v1()',
      'public.rotation_consent_read_v1(uuid)',
      'public.rotation_consent_set_v1(uuid,boolean,uuid)'
    ]) AS allowed(signature) JOIN pg_proc p
      ON p.oid=to_regprocedure(allowed.signature)
    WHERE p.proowner<>(SELECT oid FROM pg_roles WHERE rolname='macro_rotation_consent_owner')
  ) OR EXISTS (
    SELECT FROM pg_trigger WHERE tgrelid='auth.users'::regclass
      AND tgname='mmx_rotation_consent_guard_v1'
      AND tgfoid IS DISTINCT FROM to_regprocedure('auth.mmx_rotation_consent_guard_v1()')
  ) THEN
    RAISE EXCEPTION 'rotation consent function or trigger ownership mismatch';
  END IF;
END
$admit$;

-- Dedicated function ownership is a privilege boundary, not a caller-controlled
-- GUC/trigger-depth exemption. No other role receives membership in this role.
GRANT USAGE, CREATE ON SCHEMA auth, public TO macro_rotation_consent_owner;
GRANT SELECT (id,raw_user_meta_data,raw_app_meta_data),
      UPDATE (raw_app_meta_data) ON auth.users TO macro_rotation_consent_owner;

CREATE OR REPLACE FUNCTION auth.mmx_rotation_prefs_allow_v1(meta jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE SECURITY INVOKER
SET search_path=pg_catalog,pg_temp AS $fn$
  SELECT CASE
    WHEN jsonb_typeof(meta)='object'
     AND jsonb_typeof(meta->'alert_categories')='array'
    THEN meta->'alert_email_optin'='true'::jsonb
      AND meta->'alert_categories' ? 'sector_rotation_relative'
      AND NOT EXISTS (
        SELECT FROM jsonb_array_elements(meta->'alert_categories') AS x(value)
        WHERE jsonb_typeof(x.value)<>'string'
           OR (x.value #>> '{}') <> ALL (ARRAY[
             'holdings_material_change','thesis_window','fif_saved_issuer',
             'options_exposure_node','sector_rotation_relative','cs_saved_scenario'
           ])
      )
    ELSE false END IS TRUE
$fn$;

CREATE OR REPLACE FUNCTION auth.mmx_rotation_marker_valid_v1(marker jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SECURITY INVOKER
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE stamp timestamptz;
BEGIN
  IF marker IS NULL OR jsonb_typeof(marker)<>'object'
    OR NOT (marker ?& ARRAY['v','revision','active','activated_at'])
    OR marker-ARRAY['v','revision','active','activated_at']<>'{}'::jsonb
    OR (marker->'v')::text<>'1'
    OR jsonb_typeof(marker->'revision')<>'string'
    OR (marker->>'revision') !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    OR jsonb_typeof(marker->'active')<>'boolean' THEN
    RETURN false;
  END IF;
  IF marker->'active'='false'::jsonb THEN
    RETURN marker->'activated_at'='null'::jsonb;
  END IF;
  IF jsonb_typeof(marker->'activated_at')<>'string'
     OR (marker->>'activated_at') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?(Z|\+00:00)$' THEN
    RETURN false;
  END IF;
  BEGIN
    stamp := (marker->>'activated_at')::timestamptz;
    RETURN isfinite(stamp);
  EXCEPTION WHEN invalid_datetime_format OR datetime_field_overflow THEN
    RETURN false;
  END;
END
$fn$;

CREATE OR REPLACE FUNCTION auth.mmx_rotation_state_v1(uid uuid, app jsonb, meta jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY INVOKER
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE marker jsonb; result jsonb;
BEGIN
  marker := app->'rotation_notification_consent';
  result := jsonb_build_object('schema','macro.rotation_consent.v1',
    'user_id',uid,'status','inactive','active',false,
    'revision',NULL,'activated_at',NULL);
  IF (app IS NOT NULL AND jsonb_typeof(app)<>'object')
     OR (marker IS NOT NULL AND NOT auth.mmx_rotation_marker_valid_v1(marker)) THEN
    RETURN result || jsonb_build_object('status','corrupt');
  END IF;
  IF marker IS NULL THEN RETURN result; END IF;
  result := result || jsonb_build_object('revision',marker->'revision');
  IF marker->'active'='true'::jsonb THEN
    IF NOT auth.mmx_rotation_prefs_allow_v1(meta) THEN
      RETURN result || jsonb_build_object('status','preferences_not_enabled');
    END IF;
    RETURN result || jsonb_build_object('status','active','active',true,
      'activated_at',marker->'activated_at');
  END IF;
  RETURN result;
END
$fn$;

CREATE OR REPLACE FUNCTION auth.mmx_rotation_consent_guard_v1()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE old_marker jsonb; marker jsonb;
BEGIN
  IF NEW.raw_app_meta_data IS NOT NULL
     AND jsonb_typeof(NEW.raw_app_meta_data)<>'object' THEN
    RAISE EXCEPTION USING ERRCODE='22023',
      MESSAGE='rotation consent requires object app metadata';
  END IF;
  IF TG_OP='UPDATE' THEN
    old_marker := OLD.raw_app_meta_data->'rotation_notification_consent';
  END IF;
  IF current_user='macro_rotation_consent_owner' THEN
    marker := NEW.raw_app_meta_data->'rotation_notification_consent';
    IF NOT auth.mmx_rotation_marker_valid_v1(marker)
       OR (marker->'active'='true'::jsonb
           AND NOT auth.mmx_rotation_prefs_allow_v1(NEW.raw_user_meta_data)) THEN
      RAISE EXCEPTION USING ERRCODE='22023',
        MESSAGE='invalid rotation consent owner postimage';
    END IF;
    RETURN NEW;
  END IF;

  -- Generic Auth/admin writes cannot activate, erase, or restore a marker.
  -- Preserve all unrelated app-metadata keys, including their intended changes.
  IF coalesce(NEW.raw_app_meta_data ? 'rotation_notification_consent',false)
     OR old_marker IS NOT NULL THEN
    NEW.raw_app_meta_data :=
      coalesce(NEW.raw_app_meta_data,'{}'::jsonb)-'rotation_notification_consent';
    IF old_marker IS NOT NULL THEN
      NEW.raw_app_meta_data := jsonb_set(NEW.raw_app_meta_data,
        '{rotation_notification_consent}',old_marker);
    END IF;
  END IF;

  -- Every negative/malformed preference UPDATE invalidates a pending activation,
  -- even before the first marker exists or when the user was already inactive.
  -- Positive generic saves never activate. INSERT never imports activation.
  IF TG_OP='UPDATE' AND NOT auth.mmx_rotation_prefs_allow_v1(NEW.raw_user_meta_data) THEN
    marker := jsonb_build_object('v',1,'revision',gen_random_uuid(),
      'active',false,'activated_at',NULL);
    NEW.raw_app_meta_data := jsonb_set(coalesce(NEW.raw_app_meta_data,'{}'::jsonb),
      '{rotation_notification_consent}',marker);
  END IF;
  RETURN NEW;
END
$fn$;

CREATE OR REPLACE FUNCTION public.rotation_consent_read_v1(p_user_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp SET row_security=on AS $fn$
DECLARE app jsonb; meta jsonb;
BEGIN
  IF p_user_id IS NULL THEN RETURN jsonb_build_object('status','invalid_argument'); END IF;
  SELECT raw_app_meta_data,raw_user_meta_data INTO app,meta
    FROM auth.users WHERE id=p_user_id;
  IF NOT FOUND THEN RETURN jsonb_build_object('status','user_not_found'); END IF;
  RETURN jsonb_build_object('status','ok',
    'state',auth.mmx_rotation_state_v1(p_user_id,app,meta));
END
$fn$;

CREATE OR REPLACE FUNCTION public.rotation_consent_set_v1(
  p_user_id uuid,p_enabled boolean,p_expected_revision uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pg_temp SET row_security=on
SET lock_timeout='2s' SET timezone='UTC' AS $fn$
DECLARE app jsonb; meta jsonb; state jsonb; marker jsonb; revision uuid;
BEGIN
  IF p_user_id IS NULL OR p_enabled IS NULL THEN
    RETURN jsonb_build_object('status','invalid_argument');
  END IF;
  SELECT raw_app_meta_data,raw_user_meta_data INTO app,meta
    FROM auth.users WHERE id=p_user_id FOR UPDATE;
  IF NOT FOUND THEN RETURN jsonb_build_object('status','user_not_found'); END IF;
  state := auth.mmx_rotation_state_v1(p_user_id,app,meta);
  IF app IS NOT NULL AND jsonb_typeof(app)<>'object' THEN
    RETURN jsonb_build_object('status','metadata_unreadable','state',state);
  END IF;
  IF p_enabled THEN
    IF state->>'status'='corrupt' THEN
      RETURN jsonb_build_object('status','metadata_unreadable','state',state);
    END IF;
    revision := (state->>'revision')::uuid;
    IF revision IS DISTINCT FROM p_expected_revision THEN
      RETURN jsonb_build_object('status','stale_revision','state',state);
    END IF;
    IF NOT auth.mmx_rotation_prefs_allow_v1(meta) THEN
      RETURN jsonb_build_object('status','preferences_not_enabled','state',state);
    END IF;
  END IF;
  -- Revocation is authorized by the same incumbent service role, but does not
  -- require an expected revision. Both transitions serialize on this Auth row.
  marker := jsonb_build_object('v',1,'revision',gen_random_uuid(),
    'active',p_enabled,'activated_at',CASE WHEN p_enabled THEN
      to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
      ELSE NULL END);
  app := jsonb_set(coalesce(app,'{}'::jsonb),'{rotation_notification_consent}',marker);
  UPDATE auth.users SET raw_app_meta_data=app WHERE id=p_user_id;
  RETURN jsonb_build_object('status','applied',
    'state',auth.mmx_rotation_state_v1(p_user_id,app,meta));
END
$fn$;

ALTER FUNCTION auth.mmx_rotation_prefs_allow_v1(jsonb) OWNER TO macro_rotation_consent_owner;
ALTER FUNCTION auth.mmx_rotation_marker_valid_v1(jsonb) OWNER TO macro_rotation_consent_owner;
ALTER FUNCTION auth.mmx_rotation_state_v1(uuid,jsonb,jsonb) OWNER TO macro_rotation_consent_owner;
ALTER FUNCTION auth.mmx_rotation_consent_guard_v1() OWNER TO macro_rotation_consent_owner;
ALTER FUNCTION public.rotation_consent_read_v1(uuid) OWNER TO macro_rotation_consent_owner;
ALTER FUNCTION public.rotation_consent_set_v1(uuid,boolean,uuid) OWNER TO macro_rotation_consent_owner;

REVOKE ALL ON FUNCTION auth.mmx_rotation_prefs_allow_v1(jsonb),
  auth.mmx_rotation_marker_valid_v1(jsonb),
  auth.mmx_rotation_state_v1(uuid,jsonb,jsonb),
  auth.mmx_rotation_consent_guard_v1(),
  public.rotation_consent_read_v1(uuid),
  public.rotation_consent_set_v1(uuid,boolean,uuid)
  FROM PUBLIC,anon,authenticated,service_role,supabase_auth_admin;
-- Guard dependencies are pure value predicates, not enrollment authority.
GRANT EXECUTE ON FUNCTION auth.mmx_rotation_prefs_allow_v1(jsonb),
  auth.mmx_rotation_marker_valid_v1(jsonb)
  TO supabase_auth_admin,service_role;
GRANT EXECUTE ON FUNCTION public.rotation_consent_read_v1(uuid),
  public.rotation_consent_set_v1(uuid,boolean,uuid) TO service_role;
REVOKE CREATE ON SCHEMA auth,public FROM macro_rotation_consent_owner;

-- Idempotent source candidate; no user backfill and no automatic opt-in.
DROP TRIGGER IF EXISTS mmx_rotation_consent_guard_v1 ON auth.users;
CREATE TRIGGER mmx_rotation_consent_guard_v1
  BEFORE INSERT OR UPDATE OF raw_user_meta_data,raw_app_meta_data ON auth.users
  FOR EACH ROW EXECUTE FUNCTION auth.mmx_rotation_consent_guard_v1();
COMMENT ON FUNCTION public.rotation_consent_set_v1(uuid,boolean,uuid) IS
  'Macro rotation consent C0 v1: source-only primitive; service-role subject binding remains at existing account owner';
COMMIT;
