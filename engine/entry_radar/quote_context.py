"""Retain and restore an actual native identity observation in the Radar pack.

No quote acquisition, used-input assertion, extra store or historical backfill.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json

from engine.entry_radar import live_pack as lp
from engine.entry_radar.replay.identity_observation_snapshot import IdentitySnapshotRead
from lib import evidence_foundation as ef
from lib.dataos.identity import validate_reference_snapshot


class QuoteContextUnavailable(ValueError):
    """Stable refusal, without raw quote data or reader bodies."""


def _now():
    return datetime.now(timezone.utc)


def _require(ok, code):
    if not ok:
        raise QuoteContextUnavailable(code)






def _check_native_read(read: IdentitySnapshotRead) -> None:
    _require(type(read) is IdentitySnapshotRead, 'quote_identity_read_required')
    snap=read.snapshot
    checked=validate_reference_snapshot(snap.receipt_bytes,dict(snap.artifact_bytes),snap.receipt_bytes,
        alias_records=json.loads(snap.alias_json),master_records=json.loads(snap.master_json))
    publication=json.loads(snap.receipt_bytes)['publication']
    receipt=read.receipt.as_record()
    _require(checked==snap and receipt['receipt_sha256']==sha256(snap.receipt_bytes).hexdigest()
             and receipt['generation_id']==publication['generation_id']
             and receipt['history_prefix_sha256']==publication['history_sha256']
             and receipt['artifact_sha256']=={name:row['sha256'] for name,row in publication['artifacts'].items()},
             'quote_identity_snapshot_mismatch')


def retain_pack_identity(pack: lp.LivePack, read: IdentitySnapshotRead) -> lp.LivePack:
    """Retain the REAL owner read receipt in the existing nightly pack only."""
    from dataclasses import replace
    from lib.dataos.identity import ReferenceReadReceipt
    _check_native_read(read)
    receipt=ReferenceReadReceipt.from_record(read.receipt.as_record()).as_record()
    _require(int(receipt['read_completed_at_utc_ns']) <= int(_now().timestamp()*10**9), 'quote_identity_read_in_future')
    body={'schema':'entry_radar.pack_identity_observation.v1','scope':'prospective_next_session_context',
          'read_receipt':receipt}
    body['sha256']=sha256(ef.canonical_json_bytes(body)).hexdigest()
    return replace(pack,identity_observation=body)


def restore_pack_identity(pack: lp.LivePack, current_read: IdentitySnapshotRead) -> IdentitySnapshotRead:
    """Reuse a real prior read ONLY for the exact same owner generation/bytes.

    Current bytes are revalidated by the native reader. The earlier clock comes
    exclusively from its retained actual read receipt, not from mtime, pack build
    time or event time. A changed owner generation cannot be substituted for it.
    """
    from lib.dataos.identity import ReferenceReadReceipt
    try:
        _check_native_read(current_read)
        body=dict(pack.identity_observation or {})
        digest=body.pop('sha256')
        _require(set(body)=={'schema','scope','read_receipt'}
                 and body['schema']=='entry_radar.pack_identity_observation.v1'
                 and body['scope']=='prospective_next_session_context'
                 and digest==sha256(ef.canonical_json_bytes(body)).hexdigest(), 'quote_retained_identity_invalid')
        prior=ReferenceReadReceipt.from_record(body['read_receipt'])
        old,new=prior.as_record(),current_read.receipt.as_record()
        keys=('receipt_sha256','generation_id','artifact_sha256','history_prefix_sha256')
        _require(all(old[k]==new[k] for k in keys)
                 and int(old['read_completed_at_utc_ns']) <= int(new['read_started_at_utc_ns']),
                 'quote_retained_generation_mismatch')
        return IdentitySnapshotRead(current_read.snapshot,prior)
    except QuoteContextUnavailable:
        raise
    except Exception:
        raise QuoteContextUnavailable('quote_retained_identity_unavailable') from None
