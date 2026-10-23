-- Disposable authenticated-RPC fixture. Not product or production DDL.
DO $create_authenticated$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = 'authenticated'
  ) THEN
    CREATE ROLE authenticated NOLOGIN;
  END IF;
END
$create_authenticated$;

CREATE SCHEMA IF NOT EXISTS auth;

GRANT USAGE ON SCHEMA auth TO authenticated;

CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = pg_catalog
AS $fixture_auth$
  SELECT nullif(
    current_setting('request.jwt.claim.sub', true),
    ''
  )::uuid;
$fixture_auth$;

REVOKE ALL ON FUNCTION auth.uid() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;

CREATE TABLE IF NOT EXISTS public.drawings (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL,
  symbol text NOT NULL,
  kind text NOT NULL,
  data jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

ALTER TABLE public.drawings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS drawings_owner ON public.drawings;
CREATE POLICY drawings_owner ON public.drawings
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

GRANT SELECT, INSERT, UPDATE, DELETE ON public.drawings TO authenticated;
