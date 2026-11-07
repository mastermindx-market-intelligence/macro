-- Causal transaction assertions for artifacts/replace-drawings.sql.
-- Run as a database owner after fixture-ddl.sql, direct-validator.sql, and
-- replace-drawings.sql. Every drawing mutation and observation below executes
-- as authenticated with table RLS enabled.
SET ROLE authenticated;
SET request.jwt.claim.sub = '11111111-1111-4111-8111-111111111111';

DO $transaction_regressions$
DECLARE
  drawing_one constant jsonb := $json$[
    {
      "id":"d1",
      "schemaVersion":1,
      "source":"user",
      "kind":"hline",
      "points":[{"p":10.5,"t":"2024-01-01T00:00:00Z"}]
    }
  ]$json$::jsonb;
  drawing_two constant jsonb := $json$[
    {
      "id":"d2",
      "schemaVersion":1,
      "source":"user",
      "kind":"vline",
      "points":[{"p":11.25,"t":"2024-01-02T00:00:00Z"}]
    }
  ]$json$::jsonb;
  operation_a constant uuid := '21111111-1111-4111-8111-111111111111';
  operation_b constant uuid := '22222222-2222-4222-8222-222222222222';
  operation_c constant uuid := '23333333-3333-4333-8333-333333333333';
  owner_a constant uuid := '11111111-1111-4111-8111-111111111111';
  owner_b constant uuid := '12222222-2222-4222-8222-222222222222';
  result jsonb;
  revision uuid;
  response_revision uuid;
  response_revision_text text;
  operation_index integer;
  before_preimage jsonb;
  after_preimage jsonb;
  rollback_preimage jsonb;
  a_preserve_preimage jsonb;
  b_rows_preimage jsonb;
  row_count integer;
  collection_count integer;
  legacy_count integer;
  pass_count integer := 0;
BEGIN
  DELETE FROM public.drawings
  WHERE symbol IN ('TESTA', 'PRESERVE');

  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '31111111-1111-4111-8111-111111111111',
    auth.uid(),
    'TESTA',
    'hline',
    '{"id":"legacy","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":9,"t":"2023-01-01T00:00:00Z"}]}'::jsonb,
    '2024-01-01T00:00:00Z'::timestamptz
  );

  -- Case 1: an initial replacement creates exactly one collection revision.
  result := public.replace_drawings_collection(
    ' TESTA ', drawing_one, NULL, operation_a
  );
  SELECT count(*),
         count(*) FILTER (WHERE kind = '__collection_v1')
  INTO row_count, collection_count
  FROM public.drawings
  WHERE symbol = 'TESTA';
  SELECT d.data->>'revision'
  INTO response_revision_text
  FROM public.drawings d
  WHERE d.symbol = 'TESTA'
    AND d.kind = '__collection_v1';
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR result->>'idempotentReplay' IS DISTINCT FROM 'false'
    OR result->>'superseded' IS DISTINCT FROM 'false'
    OR row_count <> 1
    OR collection_count <> 1
    OR row_count <> collection_count
    OR response_revision_text IS NULL
  THEN
    RAISE EXCEPTION 'FAIL: initial insert response/row shape';
  END IF;
  revision := response_revision_text::uuid;
  response_revision := (result->>'revision')::uuid;
  IF response_revision IS DISTINCT FROM revision THEN
    RAISE EXCEPTION 'FAIL: initial insert revision';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: initial insert';

  before_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );

  -- Case 2: exact live-operation replay is a no-op.
  result := public.replace_drawings_collection(
    'TESTA', drawing_one, '99999999-9999-4999-8999-999999999999'::uuid, operation_a
  );
  after_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR result->>'idempotentReplay' IS DISTINCT FROM 'true'
    OR result->>'superseded' IS DISTINCT FROM 'false'
    OR (result->>'revision')::uuid IS DISTINCT FROM revision
    OR after_preimage IS DISTINCT FROM before_preimage
  THEN
    RAISE EXCEPTION 'FAIL: exact replay changed rows/response';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: exact replay/no-change';

  -- Case 3: the prior operation with changed payload is rejected unchanged.
  result := public.replace_drawings_collection(
    'TESTA', drawing_two, revision, operation_a
  );
  after_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );
  IF result->>'ok' IS DISTINCT FROM 'false'
    OR result->>'code' IS DISTINCT FROM 'operation_payload_mismatch'
    OR after_preimage IS DISTINCT FROM before_preimage
  THEN
    RAISE EXCEPTION 'FAIL: prior payload mismatch changed rows/response';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: prior-op payload mismatch/no-change';

  -- Case 4: stale CAS is rejected unchanged.
  result := public.replace_drawings_collection(
    'TESTA', drawing_two, NULL, operation_b
  );
  after_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );
  IF result->>'ok' IS DISTINCT FROM 'false'
    OR result->>'code' IS DISTINCT FROM 'revision_conflict'
    OR result->>'operationUnknownPossible' IS DISTINCT FROM 'true'
    OR after_preimage IS DISTINCT FROM before_preimage
  THEN
    RAISE EXCEPTION 'FAIL: stale CAS changed rows/response';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: stale CAS/no-change';

  -- Case 5: a superseded prior-operation replay is a no-op.
  result := public.replace_drawings_collection(
    'TESTA', drawing_two, revision, operation_b
  );
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR result->>'idempotentReplay' IS DISTINCT FROM 'false'
    OR result->>'superseded' IS DISTINCT FROM 'false'
    OR result->>'revision' IS NULL
  THEN
    RAISE EXCEPTION 'FAIL: admitted B write before superseded replay';
  END IF;
  revision := (result->>'revision')::uuid;
  before_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );
  result := public.replace_drawings_collection(
    'TESTA', drawing_one, NULL, operation_a
  );
  after_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR result->>'idempotentReplay' IS DISTINCT FROM 'true'
    OR result->>'superseded' IS DISTINCT FROM 'true'
    OR (result->>'revision')::uuid IS DISTINCT FROM revision
    OR after_preimage IS DISTINCT FROM before_preimage
  THEN
    RAISE EXCEPTION 'FAIL: superseded replay changed rows/response';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: prior-op superseded replay/no-change';

  -- Before clearing, refresh the exact sole-collection preimage.
  SELECT count(*),
         count(*) FILTER (WHERE kind = '__collection_v1')
  INTO row_count, collection_count
  FROM public.drawings
  WHERE symbol = 'TESTA';
  SELECT d.data->>'revision'
  INTO response_revision_text
  FROM public.drawings d
  WHERE d.symbol = 'TESTA'
    AND d.kind = '__collection_v1';
  IF row_count <> 1 OR collection_count <> 1
    OR response_revision_text IS NULL
    OR response_revision_text::uuid IS DISTINCT FROM revision
  THEN
    RAISE EXCEPTION 'FAIL: clear precondition is not one exact collection';
  END IF;
  before_preimage := (
    SELECT to_jsonb(d)
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
  );

  -- Case 6: [] clears the collection and collapses the prior-operation ring.
  result := public.replace_drawings_collection(
    'TESTA', '[]'::jsonb, revision, operation_c
  );
  SELECT count(*),
         count(*) FILTER (WHERE kind = '__collection_v1'),
         count(*) FILTER (WHERE kind <> '__collection_v1')
  INTO row_count, collection_count, legacy_count
  FROM public.drawings
  WHERE symbol = 'TESTA';
  SELECT d.data->>'revision'
  INTO response_revision_text
  FROM public.drawings d
  WHERE d.symbol = 'TESTA'
    AND d.kind = '__collection_v1';
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR row_count <> 1
    OR collection_count <> 1
    OR legacy_count <> 0
    OR response_revision_text IS NULL
    OR response_revision_text::uuid IS DISTINCT FROM (result->>'revision')::uuid
    OR jsonb_array_length((SELECT d.data->'drawings' FROM public.drawings d
                            WHERE d.symbol = 'TESTA')) <> 0
    OR jsonb_array_length((SELECT d.data->'prior_operations' FROM public.drawings d
                            WHERE d.symbol = 'TESTA')) <> 2
  THEN
    RAISE EXCEPTION 'FAIL: clear[] row/metadata shape';
  END IF;
  revision := response_revision_text::uuid;
  after_preimage := (
    SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'
  );
  IF after_preimage IS NOT DISTINCT FROM before_preimage THEN
    RAISE EXCEPTION 'FAIL: clear[] did not replace preimage';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: clear[]/prior-operation collapse';

  -- Create three preservation controls: caller A's other symbol, caller B's
  -- same symbol, and caller B's other symbol. Snapshot A under A and B under B.
  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '34343434-3434-4343-8343-343434343434',
    owner_a,
    'PRESERVE',
    'hline',
    '{"id":"same-owner-other-symbol","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":6,"t":"2023-01-01T00:00:00Z"}]}'::jsonb,
    '2024-03-01T00:00:00Z'::timestamptz
  );
  a_preserve_preimage := (
    SELECT to_jsonb(d)
    FROM public.drawings d
    WHERE d.id = '34343434-3434-4343-8343-343434343434'
  );
  IF a_preserve_preimage IS NULL THEN
    RAISE EXCEPTION 'FAIL: A PRESERVE snapshot missing under A';
  END IF;

  PERFORM set_config('request.jwt.claim.sub', owner_b::text, true);
  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '32222222-2222-4222-8222-222222222222',
    owner_b,
    'TESTA',
    'hline',
    '{"id":"other-owner-same-symbol","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":8,"t":"2023-01-01T00:00:00Z"}]}'::jsonb,
    '2024-02-01T00:00:00Z'::timestamptz
  );
  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '32323232-3232-4232-8232-323232323232',
    owner_b,
    'PRESERVE',
    'hline',
    '{"id":"other-owner-other-symbol","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":7,"t":"2023-01-01T00:00:00Z"}]}'::jsonb,
    '2024-02-01T00:00:00Z'::timestamptz
  );
  b_rows_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.id IN (
      '32222222-2222-4222-8222-222222222222'::uuid,
      '32323232-3232-4232-8232-323232323232'::uuid
    )
  );
  IF jsonb_array_length(b_rows_preimage) <> 2 THEN
    RAISE EXCEPTION 'FAIL: B did not snapshot both own rows under B';
  END IF;

  PERFORM set_config('request.jwt.claim.sub', owner_a::text, true);
  IF EXISTS (
    SELECT 1 FROM public.drawings d
    WHERE d.user_id = owner_b
  ) THEN
    RAISE EXCEPTION 'FAIL: RLS exposed another owner row to A';
  END IF;
  result := public.replace_drawings_collection(
    'TESTA', drawing_one, revision, '24444444-4444-4444-8444-444444444444'::uuid
  );
  IF result->>'ok' IS DISTINCT FROM 'true'
    OR result->>'idempotentReplay' IS DISTINCT FROM 'false'
    OR result->>'superseded' IS DISTINCT FROM 'false'
  THEN
    RAISE EXCEPTION 'FAIL: ownership isolation replacement response';
  END IF;
  revision := (result->>'revision')::uuid;
  IF EXISTS (
    SELECT 1 FROM public.drawings d
    WHERE d.user_id = owner_b
  ) THEN
    RAISE EXCEPTION 'FAIL: operation exposed another owner row to A';
  END IF;
  after_preimage := (
    SELECT to_jsonb(d)
    FROM public.drawings d
    WHERE d.id = '34343434-3434-4343-8343-343434343434'
  );
  IF after_preimage IS DISTINCT FROM a_preserve_preimage THEN
    RAISE EXCEPTION 'FAIL: A PRESERVE changed under A';
  END IF;

  PERFORM set_config('request.jwt.claim.sub', owner_b::text, true);
  after_preimage := (
    SELECT COALESCE(jsonb_agg(to_jsonb(d) ORDER BY d.id), '[]'::jsonb)
    FROM public.drawings d
    WHERE d.id IN (
      '32222222-2222-4222-8222-222222222222'::uuid,
      '32323232-3232-4232-8232-323232323232'::uuid
    )
  );
  IF after_preimage IS DISTINCT FROM b_rows_preimage THEN
    RAISE EXCEPTION 'FAIL: B same/other symbol rows changed under B';
  END IF;
  PERFORM set_config('request.jwt.claim.sub', owner_a::text, true);
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: owner/symbol isolation preservation';

  -- Case 7: rollback restores the exact whole object after a verified write.
  rollback_preimage := (
    SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'
  );
  result := NULL;
  BEGIN
    result := public.replace_drawings_collection(
      'TESTA', drawing_two, revision,
      '25555555-5555-4555-8555-555555555555'::uuid
    );
    IF result->>'ok' IS DISTINCT FROM 'true'
      OR result->>'idempotentReplay' IS DISTINCT FROM 'false'
      OR result->>'superseded' IS DISTINCT FROM 'false'
    THEN
      RAISE EXCEPTION 'FAIL: rollback operation did not succeed'
        USING ERRCODE = 'P0001';
    END IF;
    revision := (result->>'revision')::uuid;
    SELECT count(*),
           count(*) FILTER (WHERE kind = '__collection_v1')
    INTO row_count, collection_count
    FROM public.drawings
    WHERE symbol = 'TESTA';
    SELECT d.data->>'revision'
    INTO response_revision_text
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
      AND d.kind = '__collection_v1';
    IF row_count <> 1
      OR collection_count <> 1
      OR response_revision_text IS NULL
      OR response_revision_text::uuid IS DISTINCT FROM revision
      OR (SELECT d.data->'drawings' FROM public.drawings d
          WHERE d.symbol = 'TESTA') IS DISTINCT FROM drawing_two
    THEN
      RAISE EXCEPTION 'FAIL: rollback write was not visible before rollback'
        USING ERRCODE = 'P0001';
    END IF;
    RAISE EXCEPTION 'transaction-regressions forced rollback'
      USING ERRCODE = '23505';
  EXCEPTION
    WHEN SQLSTATE '23505' THEN
      IF result->>'ok' IS DISTINCT FROM 'true' THEN
        RAISE EXCEPTION 'FAIL: caught function failure as forced rollback';
      END IF;
      after_preimage := (
        SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'
      );
      IF after_preimage IS DISTINCT FROM rollback_preimage THEN
        RAISE EXCEPTION 'FAIL: rollback did not restore exact whole object';
      END IF;
    WHEN OTHERS THEN
      RAISE EXCEPTION 'FAIL: rollback test caught unexpected function error';
  END;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: subtransaction rollback exact whole object';

  -- Case 8: the prior-operation ring reaches and remains bounded at 32.
  FOR operation_index IN 0..32 LOOP
    SELECT count(*),
           count(*) FILTER (WHERE kind = '__collection_v1')
    INTO row_count, collection_count
    FROM public.drawings
    WHERE symbol = 'TESTA';
    IF row_count <> 1 OR collection_count <> 1
    THEN
      RAISE EXCEPTION 'FAIL: ring setup precondition %', operation_index;
    END IF;
    SELECT d.data->>'revision'
    INTO response_revision_text
    FROM public.drawings d
    WHERE d.symbol = 'TESTA'
      AND d.kind = '__collection_v1';
    revision := response_revision_text::uuid;
    result := public.replace_drawings_collection(
      'TESTA',
      drawing_one,
      revision,
      gen_random_uuid()
    );
    IF result->>'ok' IS DISTINCT FROM 'true'
      OR result->>'idempotentReplay' IS DISTINCT FROM 'false'
      OR result->>'superseded' IS DISTINCT FROM 'false'
    THEN
      RAISE EXCEPTION 'FAIL: ring setup operation %', operation_index;
    END IF;
  END LOOP;
  SELECT count(*),
         count(*) FILTER (WHERE kind = '__collection_v1')
  INTO row_count, collection_count
  FROM public.drawings
  WHERE symbol = 'TESTA';
  SELECT d.data->>'revision'
  INTO response_revision_text
  FROM public.drawings d
  WHERE d.symbol = 'TESTA'
    AND d.kind = '__collection_v1';
  IF row_count <> 1
    OR collection_count <> 1
    OR response_revision_text IS NULL
    OR response_revision_text::uuid IS DISTINCT FROM (result->>'revision')::uuid
    OR jsonb_array_length((SELECT d.data->'prior_operations' FROM public.drawings d
                            WHERE d.symbol = 'TESTA')) <> 32
  THEN
    RAISE EXCEPTION 'FAIL: ring bound/row shape';
  END IF;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: ring bound 32';

  -- Case 9: malformed live collection metadata raises 22000 and preserves it.
  DELETE FROM public.drawings WHERE symbol = 'TESTA';
  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '33445566-7788-4999-8aaa-bbbbccccdddd',
    auth.uid(),
    'TESTA',
    '__collection_v1',
    '{"schemaVersion":1}'::jsonb,
    clock_timestamp()
  );
  before_preimage := (
    SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'
  );
  result := NULL;
  BEGIN
    result := public.replace_drawings_collection(
      'TESTA', drawing_one, NULL, '35555555-6666-4777-8888-9999aaaaBBBB'::uuid
    );
    RAISE EXCEPTION 'FAIL: malformed metadata returned instead of failing'
      USING ERRCODE = 'P0001';
  EXCEPTION
    WHEN SQLSTATE '22000' THEN
      after_preimage := (
        SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'
      );
      IF after_preimage IS DISTINCT FROM before_preimage THEN
        RAISE EXCEPTION 'FAIL: malformed metadata changed preimage';
      END IF;
    WHEN OTHERS THEN
      RAISE EXCEPTION 'FAIL: malformed metadata wrong SQLSTATE';
  END;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: malformed legacy collection refusal/no-change';

  -- Case 10: direct invalid input preserves both target and unrelated rows.
  DELETE FROM public.drawings WHERE symbol = 'TESTA';
  INSERT INTO public.drawings (
    id, user_id, symbol, kind, data, created_at
  ) VALUES (
    '36666666-7777-4888-8999-aaaabbbbcccc',
    auth.uid(),
    'TESTA',
    'hline',
    '{"id":"invalid-input-target","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":5,"t":"2023-01-01T00:00:00Z"}]}'::jsonb,
    clock_timestamp()
  );
  before_preimage := jsonb_build_object(
    'target',
    (SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'),
    'unrelated',
    (SELECT to_jsonb(d) FROM public.drawings d
      WHERE d.id = '34343434-3434-4343-8343-343434343434')
  );
  result := NULL;
  BEGIN
    result := public.replace_drawings_collection(
      'TESTA', '{"invalid":"payload"}'::jsonb, NULL,
      '37777777-8888-4999-9aaa-bbbbccccdddd'::uuid
    );
    RAISE EXCEPTION 'FAIL: invalid input returned instead of failing'
      USING ERRCODE = 'P0001';
  EXCEPTION
    WHEN SQLSTATE '22023' THEN
      after_preimage := jsonb_build_object(
        'target',
        (SELECT to_jsonb(d) FROM public.drawings d WHERE d.symbol = 'TESTA'),
        'unrelated',
        (SELECT to_jsonb(d) FROM public.drawings d
          WHERE d.id = '34343434-3434-4343-8343-343434343434')
      );
      IF after_preimage IS DISTINCT FROM before_preimage THEN
        RAISE EXCEPTION 'FAIL: invalid input changed target/unrelated rows';
      END IF;
    WHEN OTHERS THEN
      RAISE EXCEPTION 'FAIL: invalid input wrong SQLSTATE';
  END;
  pass_count := pass_count + 1;
  RAISE NOTICE 'PASS: direct invalid input/no-change';

  IF pass_count <> 11 THEN
    RAISE EXCEPTION 'FAIL: expected 11 transaction cases, got %', pass_count;
  END IF;

  RAISE NOTICE 'ACTUAL_TRANSACTION_CASES=%', pass_count;
END;
$transaction_regressions$;

RESET request.jwt.claim.sub;
RESET ROLE;
