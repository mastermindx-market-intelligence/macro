CREATE ROLE authenticated;
CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
CREATE TABLE public.fixture_preimage(id integer PRIMARY KEY, body jsonb);
INSERT INTO public.fixture_preimage VALUES(1,'{"preserved":true}');
GRANT SELECT,DELETE ON public.fixture_preimage TO authenticated;
