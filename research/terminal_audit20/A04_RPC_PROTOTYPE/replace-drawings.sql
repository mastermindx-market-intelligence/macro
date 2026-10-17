-- Artifact-only existing-table transaction prototype; not production DDL.
-- Requires public.validate_drawing_replace_input from the accepted guard.
CREATE OR REPLACE FUNCTION public.replace_drawings_collection(
  p_symbol text,
  p_drawings jsonb,
  p_expected_revision uuid,
  p_operation_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog
AS $replace_drawings_collection$
DECLARE
  trim_chars CONSTANT text := chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(32)||chr(160)||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288)||chr(65279);
  owner_id uuid;
  normalized_symbol text;
  payload_hash text;
  new_revision uuid;
  live_collection_id uuid;
  live_data jsonb;
  live_revision uuid;
  live_operation_id uuid;
  live_payload_hash text;
  live_prior_operations jsonb;
  receipt jsonb;
  receipt_operation_id uuid;
  receipt_revision uuid;
  receipt_payload_hash text;
  receipt_committed_at timestamptz;
  seen_ring_operations uuid[] := '{}'::uuid[];
  ring_has_operation boolean := false;
  ring_payload_hash text;
  live_committed_at timestamptz;
  new_ring jsonb;
BEGIN
  PERFORM public.validate_drawing_replace_input(
    p_symbol,
    p_drawings,
    p_operation_id
  );

  owner_id := auth.uid();
  normalized_symbol := btrim(p_symbol, trim_chars);
  payload_hash := encode(
    pg_catalog.sha256(pg_catalog.convert_to(p_drawings::text, 'UTF8')),
    'hex'
  );

  PERFORM pg_advisory_xact_lock(
    hashtextextended(jsonb_build_array(owner_id, normalized_symbol)::text, 0)
  );

  PERFORM 1
  FROM public.drawings
  WHERE user_id = owner_id
    AND symbol = normalized_symbol
  ORDER BY created_at DESC, id DESC
  FOR UPDATE;

  SELECT id, data
  INTO live_collection_id, live_data
  FROM public.drawings
  WHERE user_id = owner_id
    AND symbol = normalized_symbol
    AND kind = '__collection_v1'
  ORDER BY created_at DESC, id DESC
  LIMIT 1;

  IF live_collection_id IS NOT NULL THEN
    SELECT created_at INTO live_committed_at
    FROM public.drawings
    WHERE id = live_collection_id;

    IF jsonb_typeof(live_data) IS DISTINCT FROM 'object'
      OR live_data->'schemaVersion' IS DISTINCT FROM '1'::jsonb
      OR jsonb_typeof(live_data->'drawings') IS DISTINCT FROM 'array'
      OR jsonb_typeof(live_data->'prior_operations') IS DISTINCT FROM 'array'
      OR jsonb_array_length(live_data->'prior_operations') > 32
      OR jsonb_typeof(live_data->'revision') IS DISTINCT FROM 'string'
      OR jsonb_typeof(live_data->'operation_id') IS DISTINCT FROM 'string'
      OR jsonb_typeof(live_data->'payload_hash') IS DISTINCT FROM 'string'
      OR live_data->>'payload_hash' !~ '^[0-9a-f]{64}$'
    THEN
      RAISE EXCEPTION 'Malformed live collection metadata'
        USING ERRCODE = '22000';
    END IF;

    BEGIN
      live_revision := (live_data->>'revision')::uuid;
      live_operation_id := (live_data->>'operation_id')::uuid;
      live_payload_hash := live_data->>'payload_hash';
      live_prior_operations := live_data->'prior_operations';
    EXCEPTION WHEN OTHERS THEN
      RAISE EXCEPTION 'Malformed live collection metadata'
        USING ERRCODE = '22000';
    END;

    IF live_revision IS NULL
      OR live_operation_id IS NULL
      OR live_payload_hash IS NULL
    THEN
      RAISE EXCEPTION 'Malformed live collection metadata'
        USING ERRCODE = '22000';
    END IF;

    FOR receipt IN
      SELECT value
      FROM jsonb_array_elements(live_prior_operations)
    LOOP
      IF jsonb_typeof(receipt) IS DISTINCT FROM 'object'
        OR jsonb_typeof(receipt->'operation_id') IS DISTINCT FROM 'string'
        OR jsonb_typeof(receipt->'revision') IS DISTINCT FROM 'string'
        OR jsonb_typeof(receipt->'payload_hash') IS DISTINCT FROM 'string'
        OR jsonb_typeof(receipt->'committed_at') IS DISTINCT FROM 'string'
        OR receipt->>'payload_hash' !~ '^[0-9a-f]{64}$'
      THEN
        RAISE EXCEPTION 'Malformed live collection prior operation'
          USING ERRCODE = '22000';
      END IF;

      BEGIN
        receipt_operation_id := (receipt->>'operation_id')::uuid;
        receipt_revision := (receipt->>'revision')::uuid;
        receipt_payload_hash := receipt->>'payload_hash';
        receipt_committed_at := (receipt->>'committed_at')::timestamptz;
      EXCEPTION WHEN OTHERS THEN
        RAISE EXCEPTION 'Malformed live collection prior operation'
          USING ERRCODE = '22000';
      END;

      IF receipt_operation_id = ANY(seen_ring_operations) THEN
        RAISE EXCEPTION 'Duplicate prior operation id'
          USING ERRCODE = '22000';
      END IF;
      seen_ring_operations := array_append(seen_ring_operations, receipt_operation_id);

      IF receipt_operation_id = p_operation_id THEN
        ring_has_operation := true;
        ring_payload_hash := receipt_payload_hash;
      END IF;
    END LOOP;

    IF live_operation_id = p_operation_id THEN
      IF live_payload_hash = payload_hash THEN
        RETURN jsonb_build_object(
          'ok', true,
          'idempotentReplay', true,
          'superseded', false,
          'revision', live_revision
        );
      END IF;

      RETURN jsonb_build_object(
        'ok', false,
        'code', 'operation_payload_mismatch'
      );
    END IF;

    IF ring_has_operation THEN
      IF ring_payload_hash = payload_hash THEN
        RETURN jsonb_build_object(
          'ok', true,
          'idempotentReplay', true,
          'superseded', true,
          'revision', live_revision
        );
      END IF;

      RETURN jsonb_build_object(
        'ok', false,
        'code', 'operation_payload_mismatch'
      );
    END IF;
  END IF;

  IF p_expected_revision IS DISTINCT FROM live_revision THEN
    RETURN jsonb_build_object(
      'ok', false,
      'code', 'revision_conflict',
      'operationUnknownPossible', true
    );
  END IF;

  new_revision := pg_catalog.gen_random_uuid();
  new_ring := '[]'::jsonb;

  IF live_collection_id IS NOT NULL THEN
    new_ring := jsonb_build_array(
      jsonb_build_object(
        'operation_id', live_operation_id,
        'revision', live_revision,
        'payload_hash', live_payload_hash,
        'committed_at', live_committed_at
      )
    );

    FOR receipt IN
      SELECT value
      FROM jsonb_array_elements(live_prior_operations)
    LOOP
      EXIT WHEN jsonb_array_length(new_ring) = 32;
      new_ring := new_ring || receipt;
    END LOOP;
  END IF;

  DELETE FROM public.drawings
  WHERE user_id = owner_id
    AND symbol = normalized_symbol;

  INSERT INTO public.drawings (
    id,
    user_id,
    symbol,
    kind,
    data,
    created_at
  ) VALUES (
    pg_catalog.gen_random_uuid(),
    owner_id,
    normalized_symbol,
    '__collection_v1',
    jsonb_build_object(
      'schemaVersion', 1,
      'drawings', p_drawings,
      'revision', new_revision,
      'operation_id', p_operation_id,
      'payload_hash', payload_hash,
      'prior_operations', new_ring
    ),
    clock_timestamp()
  );

  RETURN jsonb_build_object(
    'ok', true,
    'idempotentReplay', false,
    'superseded', false,
    'revision', new_revision
  );
END;
$replace_drawings_collection$;

REVOKE ALL ON FUNCTION public.replace_drawings_collection(text, jsonb, uuid, uuid)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.replace_drawings_collection(text, jsonb, uuid, uuid)
  TO authenticated;
