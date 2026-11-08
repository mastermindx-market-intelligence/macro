-- VALIDATION ONLY: artifact prototype, not a production migration or deployed RPC.
-- Source64c1; point bounds derived from actual DRAWING_TOOLS export. No table writes.
CREATE OR REPLACE FUNCTION public.validate_drawing_replace_input(p_symbol text, p_drawings jsonb, p_operation_id uuid)
RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog AS $guard$
DECLARE
 owner_id uuid := auth.uid(); normalized_symbol text; symbol_units integer;
 trim_chars CONSTANT text := chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(32)||chr(160)||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288)||chr(65279);
 drawing jsonb; point jsonb; bounds jsonb; drawing_id text; kind text; point_count integer;
 seen_ids text[] := '{}'::text[]; price double precision;
 rules CONSTANT jsonb := $rules${"trendline":{"min":2,"max":2},"ray":{"min":2,"max":2},"infoline":{"min":2,"max":2},"extendedline":{"min":2,"max":2},"trendangle":{"min":2,"max":2},"hline":{"min":1,"max":1},"horizontalray":{"min":1,"max":1},"vline":{"min":1,"max":1},"crossline":{"min":1,"max":1},"channel":{"min":3,"max":3},"regressiontrend":{"min":2,"max":2},"flattopbottom":{"min":3,"max":3},"disjointchannel":{"min":4,"max":4},"pitchfork":{"min":3,"max":3},"schiffpitchfork":{"min":3,"max":3},"modifiedschiffpitchfork":{"min":3,"max":3},"insidepitchfork":{"min":3,"max":3},"fib":{"min":2,"max":2},"fibtrend":{"min":3,"max":3},"fibchannel":{"min":3,"max":3},"fibtimezone":{"min":2,"max":2},"fibspeedresistancefan":{"min":2,"max":2},"trendbasedfibtime":{"min":3,"max":3},"fibcircles":{"min":2,"max":2},"fibspiral":{"min":2,"max":2},"fibspeedresistancearcs":{"min":2,"max":2},"fibwedge":{"min":3,"max":3},"pitchfan":{"min":3,"max":3},"gannbox":{"min":2,"max":2},"gannsquarefixed":{"min":2,"max":2},"gannsquare":{"min":2,"max":2},"gannfan":{"min":2,"max":2},"xabcd":{"min":5,"max":5},"cypher":{"min":5,"max":5},"headandshoulders":{"min":7,"max":7},"abcd":{"min":4,"max":4},"trianglepattern":{"min":4,"max":4},"threedrives":{"min":7,"max":7},"elliottimpulse":{"min":6,"max":6},"elliottcorrection":{"min":4,"max":4},"elliotttriangle":{"min":6,"max":6},"elliottdoublecombo":{"min":4,"max":4},"elliotttriplecombo":{"min":6,"max":6},"cycliclines":{"min":2,"max":2},"timecycles":{"min":2,"max":2},"sineline":{"min":2,"max":2},"longposition":{"min":2,"max":3},"shortposition":{"min":2,"max":3},"forecast":{"min":2,"max":2},"ghostfeed":{"min":2,"max":64},"barpattern":{"min":2,"max":2},"sector":{"min":3,"max":3},"anchoredvwap":{"min":1,"max":1},"fixedrangevolumeprofile":{"min":2,"max":2},"pricerange":{"min":2,"max":2},"daterange":{"min":2,"max":2},"dateandpricerange":{"min":2,"max":2},"measure":{"min":2,"max":2},"brush":{"min":2,"max":64},"highlighter":{"min":2,"max":64},"path":{"min":2,"max":64},"rect":{"min":2,"max":2},"rotatedrect":{"min":3,"max":3},"ellipse":{"min":3,"max":3},"circle":{"min":2,"max":2},"triangle":{"min":3,"max":3},"polyline":{"min":2,"max":64},"arc":{"min":3,"max":3},"curve":{"min":2,"max":3},"doublecurve":{"min":2,"max":4},"arrowmarker":{"min":1,"max":1},"arrow":{"min":2,"max":2},"arrowmarkleft":{"min":1,"max":1},"arrowmarkright":{"min":1,"max":1},"arrowmarktop":{"min":1,"max":1},"arrowmarkbottom":{"min":1,"max":1},"flagmark":{"min":1,"max":1},"momentum":{"min":2,"max":2},"flow":{"min":2,"max":2},"emphasis":{"min":2,"max":2},"whisper":{"min":2,"max":2},"subtle":{"min":2,"max":2},"divergence":{"min":2,"max":4},"journey":{"min":2,"max":6},"fork":{"min":2,"max":5},"threepaths":{"min":2,"max":5},"burj":{"min":2,"max":3},"text":{"min":1,"max":1},"anchoredtext":{"min":1,"max":1},"note":{"min":1,"max":1},"anchorednote":{"min":1,"max":1},"callout":{"min":2,"max":2},"pricelabel":{"min":1,"max":1},"pricenote":{"min":1,"max":1},"signpost":{"min":1,"max":1},"comment":{"min":1,"max":1},"image":{"min":2,"max":2},"emoji":{"min":1,"max":1},"icon":{"min":1,"max":1}}$rules$::jsonb;
BEGIN
 IF owner_id IS NULL THEN RAISE EXCEPTION 'Authentication required' USING ERRCODE='28000'; END IF;
 IF p_operation_id IS NULL THEN RAISE EXCEPTION 'Operation id required' USING ERRCODE='22023'; END IF;
 IF p_symbol IS NULL THEN RAISE EXCEPTION 'Invalid symbol' USING ERRCODE='22023'; END IF;
 normalized_symbol:=btrim(p_symbol,trim_chars);
 IF char_length(normalized_symbol) NOT BETWEEN 1 AND 64 THEN RAISE EXCEPTION 'Invalid symbol' USING ERRCODE='22023'; END IF;
 SELECT char_length(normalized_symbol)+count(*) FILTER (WHERE ascii(substr(normalized_symbol,i,1))>65535) INTO symbol_units FROM generate_series(1,char_length(normalized_symbol)) chars(i);
 IF symbol_units>64 THEN RAISE EXCEPTION 'Symbol exceeds64 UTF16 units' USING ERRCODE='22023'; END IF;
 IF jsonb_typeof(p_drawings) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Array required' USING ERRCODE='22023'; END IF;
 IF jsonb_array_length(p_drawings)>500 OR octet_length(convert_to(p_drawings::text,'UTF8'))>2000000 THEN
  RAISE EXCEPTION 'Payload too large' USING ERRCODE='22023';
 END IF;
 FOR drawing IN SELECT value FROM jsonb_array_elements(p_drawings) LOOP
  IF jsonb_typeof(drawing) IS DISTINCT FROM 'object' OR jsonb_typeof(drawing->'id') IS DISTINCT FROM 'string' THEN
   RAISE EXCEPTION 'Invalid drawing or id' USING ERRCODE='22023';
  END IF;
  drawing_id:=btrim(drawing->>'id',trim_chars);
  IF drawing_id='' OR drawing_id=ANY(seen_ids) THEN RAISE EXCEPTION 'Empty or duplicate id' USING ERRCODE='22023'; END IF;
  seen_ids:=array_append(seen_ids,drawing_id);
  IF drawing->'schemaVersion' IS DISTINCT FROM '1'::jsonb OR drawing->>'source' IS DISTINCT FROM 'user' THEN
   RAISE EXCEPTION 'Canonical user drawing required' USING ERRCODE='22023';
  END IF;
  IF jsonb_typeof(drawing->'kind') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'Kind required' USING ERRCODE='22023'; END IF;
  kind:=drawing->>'kind'; bounds:=rules->kind;
  IF bounds IS NULL OR jsonb_typeof(drawing->'points') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'Invalid kind or points' USING ERRCODE='22023'; END IF;
  point_count:=jsonb_array_length(drawing->'points');
  IF point_count<(bounds->>'min')::integer OR point_count>(bounds->>'max')::integer THEN RAISE EXCEPTION 'Invalid point count' USING ERRCODE='22023'; END IF;
  FOR point IN SELECT value FROM jsonb_array_elements(drawing->'points') LOOP
   IF jsonb_typeof(point) IS DISTINCT FROM 'object' OR jsonb_typeof(point->'p') IS DISTINCT FROM 'number' THEN
    RAISE EXCEPTION 'Numeric price required' USING ERRCODE='22023';
   END IF;
   BEGIN
    price:=(point->>'p')::double precision;
   EXCEPTION WHEN numeric_value_out_of_range THEN
    RAISE EXCEPTION 'Price outside finite double range' USING ERRCODE='22023';
   END;
   IF price='Infinity'::double precision OR price='-Infinity'::double precision OR price='NaN'::double precision THEN
    RAISE EXCEPTION 'Finite price required' USING ERRCODE='22023';
   END IF;
   IF jsonb_typeof(point->'t') IS NULL OR jsonb_typeof(point->'t') NOT IN ('string','number') OR btrim(point->>'t',trim_chars)='' THEN
    RAISE EXCEPTION 'Nonempty supported time required' USING ERRCODE='22023';
   END IF;
  END LOOP;
 END LOOP;
END;
$guard$;
REVOKE ALL ON FUNCTION public.validate_drawing_replace_input(text,jsonb,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.validate_drawing_replace_input(text,jsonb,uuid) TO authenticated;
