-- 0009 ROLLBACK — removes the Catalyst consent v2 triggers and functions.
-- Order: triggers first (so the incumbent email tables lose their hooks before the
-- trigger functions go), then the trigger functions, then the seven RPCs.
-- The two ledger tables are RETAINED on purpose: they hold confirmed grants and the
-- replay ledger; dropping them is a separate owner decision, not part of a rollback.
-- After this file the application's boot probe answers CONSENT_OWNER_NOT_READY and the
-- opt-in funnel refuses; incumbent unsubscribe/preference writes are unaffected.
-- Apply path: scripts/deploy/catalyst_consent_migrate.py --rollback (same route as --apply).
begin;
set local lock_timeout = '3s';
set local statement_timeout = '60s';

drop trigger if exists catalyst_consent_global_address_revocation on public.email_suppression;
drop trigger if exists catalyst_consent_global_user_revocation on public.email_prefs;
drop trigger if exists catalyst_consent_grant_immutable on public.catalyst_consent_grants;

drop function if exists public.catalyst_consent_on_global_address_suppression();
drop function if exists public.catalyst_consent_on_global_user_optout();
drop function if exists public.catalyst_consent_grant_guard();

drop function if exists public.catalyst_consent_contract();
drop function if exists public.catalyst_consent_begin(text,text,text);
drop function if exists public.catalyst_consent_resolve(text,text);
drop function if exists public.catalyst_consent_confirm(uuid,text,text,text[],text,text,jsonb);
drop function if exists public.catalyst_consent_current(uuid,text);
drop function if exists public.catalyst_consent_interested(text,integer);
drop function if exists public.catalyst_consent_revoke(uuid,text,text);

-- Tables public.catalyst_consent_pending / public.catalyst_consent_grants retained.
commit;
