"""Closed schema dispatch on the incumbent fixed native helper/frame only."""
import struct
from . import market_memory_e0_native_issuer as legacy
from . import market_memory_e0_evaluation_issuer as evaluation

def serve(input_stream,output_stream):
    header=input_stream.read(4)
    if len(header)!=4:return _legacy_frame_refusal(output_stream)
    size=struct.unpack('>I',header)[0]
    if not 0<size<=16384:return _legacy_frame_refusal(output_stream)
    raw=input_stream.read(size)
    if len(raw)!=size or input_stream.read(1)!=b'':return _legacy_frame_refusal(output_stream)
    # Unknown versions remain handled/refused by the unchanged original owner.
    try:value=legacy.decode(raw,16384)
    except Exception:
        response=legacy.exchange(raw)
    else:
        if value.get('schema')==evaluation.data.REQUEST:
            try:response=evaluation.exchange(raw)
            except evaluation.EvaluationSourceError:raise SystemExit(77) from None
        else:response=legacy.exchange(raw)
    output_stream.write(struct.pack('>I',len(response))+response);output_stream.flush()


def _legacy_frame_refusal(output_stream):
    raw=legacy.canonical(legacy._refusal('wire_invalid'))
    output_stream.write(struct.pack('>I',len(raw))+raw);output_stream.flush()
