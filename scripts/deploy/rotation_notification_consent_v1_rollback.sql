-- Source-only rollback candidate. Hold activation before rollback.
-- Keep existing marker data: deletion would erase revocation history.
-- Missing RPCs must fail closed in every future consumer.
BEGIN;
DROP TRIGGER IF EXISTS mmx_rotation_consent_guard_v1 ON auth.users;
DROP FUNCTION IF EXISTS public.rotation_consent_set_v1(uuid,boolean,uuid);
DROP FUNCTION IF EXISTS public.rotation_consent_read_v1(uuid);
DROP FUNCTION IF EXISTS auth.mmx_rotation_consent_guard_v1();
DROP FUNCTION IF EXISTS auth.mmx_rotation_state_v1(uuid,jsonb,jsonb);
DROP FUNCTION IF EXISTS auth.mmx_rotation_marker_valid_v1(jsonb);
DROP FUNCTION IF EXISTS auth.mmx_rotation_prefs_allow_v1(jsonb);
REVOKE SELECT(id,raw_user_meta_data,raw_app_meta_data),
  UPDATE(raw_app_meta_data) ON auth.users FROM macro_rotation_consent_owner;
REVOKE USAGE,CREATE ON SCHEMA auth,public FROM macro_rotation_consent_owner;
DROP ROLE macro_rotation_consent_owner;
COMMIT;
