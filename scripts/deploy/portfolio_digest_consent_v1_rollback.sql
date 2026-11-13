-- Stop digest enrollment without erasing any committed withdrawal fence.
-- Keep columns, revision guards, RLS and restricted deletion permissions intact.
-- The private role has no login or memberships; removing its only callable
-- positive transition prevents legacy positive writes from bypassing the fence.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DROP FUNCTION IF EXISTS public.portfolio_digest_consent_set_v1(uuid,boolean,uuid);
COMMIT;
