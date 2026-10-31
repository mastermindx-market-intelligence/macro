"""Qualified owner evidence composition; supplies no host/resource authority.

An installed owner entry constructs this provider from its actual six-assertion
controller. Its private binding methods join live original inputs; they do not
select a route, create a reservation, infer exclusion or issue an admission.
Default daily/CLI entry selection and the public HTTPS refusal are unchanged.
"""
from hashlib import sha256
from functools import wraps
import os
from pathlib import Path
import sys
import time

_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(_ROOT))

from scripts.ci.qledger_owner_evidence import OrdinaryPublicationEvidence, EvidenceUnavailable
from scripts.ci.qledger_owner_invocation import record_publication_assertion_refusal

_ASSERTIONS=('assert_bootstrap_exclusion','assert_launcher_coverage','assert_resources',
             'assert_publication_readback','assert_descendants_settled','assert_process_version')


def _require(value,message):
    if not value:raise EvidenceUnavailable(message)


def _sticky_assertion(method):
    @wraps(method)
    def guarded(self,**context):
        try:
            self._check()
            return method(self,**context)
        except BaseException as exc:
            # Includes pre-attempt and conversion assertions with no native
            # publication scope. A caller wrapper cannot erase this failure.
            self.failure=self.failure or exc
            record_publication_assertion_refusal(exc)
            raise
    return guarded


class OwnerEntryEvidence:
    """Compose attested controller assertions with actual publication evidence."""
    def __init__(self,context,authority,*,conversion_origin_binding_sha256):
        self.context,self.authority=context,authority
        self.loader=globals().get('__loader__')
        _require(getattr(self.loader,'_qledger_bootstrap_active',False),
                 'owner controller requires the qualified finite loader')
        self.pid,self.endpoint=os.getpid(),context.original_deadline_monotonic_ns
        self.original=self.reader=self.failure=None
        self.native=None
        self.conversion=OrdinaryPublicationEvidence(context,origin_binding_sha256=conversion_origin_binding_sha256)
        self._check()

    def _check(self):
        if self.failure is not None:raise self.failure
        self.loader.check()
        _require(os.getpid()==self.pid and self.context.original_deadline_monotonic_ns==self.endpoint
                 and type(self.endpoint) is int and time.monotonic_ns()<self.endpoint,
                 'original owner context/process/endpoint changed')
        _require(self.authority is not None and type(self.authority) not in (bool,dict),
                 'actual external controller authority required')
        self.loader.callable(type(self.authority))
        for name in _ASSERTIONS:self.loader.callable(getattr(self.authority,name,None))

    def _loaded(self,loaded):
        self._check()
        _require(loaded.context is self.context and loaded.bundle is self.loader
                 and loaded.gate.evidence.provider is self,
                 'different loaded owner/provider context')
        loaded.deadline.check()

    def _carriers(self,carriers,origin):
        from scripts.ci.qledger_engine_publisher import CheckoutHTTPSCarrier
        seen=set();fds=set()
        for carrier in carriers:
            _require(type(carrier) is CheckoutHTTPSCarrier and id(carrier) not in seen,
                     'distinct typed original HTTPS carriers required')
            seen.add(id(carrier))
            _require(carrier.pid==self.pid and carrier.repo==self.context.repo
                     and sha256(carrier.destination.encode()).hexdigest()==origin
                     and carrier._attempt is None and not carrier._use_lock.locked(),
                     'foreign, transferred or used original HTTPS carrier')
            carrier.check()
            for fd in (carrier.git_dir,carrier.config_fd,carrier.ca_fd):
                if fd is not None:
                    _require(fd not in fds,'shared original credential descriptor refused')
                    fds.add(fd);os.fstat(fd)

    def _bind_native_original(self,loaded,owner_binding,publication,*,anchor_carrier):
        """Called by qualified owner entry after actual original inputs exist."""
        self._loaded(loaded)
        _require(self.original is None and self.reader is None,'owner invocation is already bound')
        from scripts.ci.qledger_engine_publisher import NativePublicationFinalizer
        from engine.qledger_original_result import OriginalResultClaimsBinding
        _require(type(owner_binding) is OriginalResultClaimsBinding
                 and owner_binding.original_process_id==self.pid and owner_binding.repo_root==self.context.repo
                 and type(publication) is NativePublicationFinalizer and publication.pid==self.pid,
                 'exact creator native owner/finalizer required')
        original=loaded.config['producer_context']
        _require(type(original) is dict and set(original)=={'operation_id','lane_id','budget_id','retention_id'}
                 and (owner_binding.operation_id,owner_binding.lane_id)==(original['operation_id'],original['lane_id'])
                 and loaded.gate.producers.get((original['operation_id'],original['lane_id']))
                     ==(original['budget_id'],original['retention_id']),
                 'original operation/lane/resource binding differs')
        origin=publication.original['origin_binding_sha256']
        publish_carrier=publication.original.get('https_carrier')
        self._carriers((anchor_carrier,publish_carrier),origin)
        self.original=(owner_binding,publication,anchor_carrier,publish_carrier,dict(original),dict(publication.original))
        self.native=OrdinaryPublicationEvidence(self.context,origin_binding_sha256=origin,
                                               native_anchor_carrier=anchor_carrier)

    def _require_native_original(self,loaded,binding,publication):
        self._loaded(loaded)
        _require(self.original is not None and self.original[0] is binding and self.original[1] is publication
                 and self.original[4]==loaded.config['producer_context'] and self.original[5]==publication.original,
                 'actual bound owner original is absent or replaced')
        _require((binding.operation_id,binding.lane_id)==(self.original[4]['operation_id'],self.original[4]['lane_id'])
                 and binding.original_process_id==self.pid and binding.repo_root==self.context.repo,
                 'actual bound owner original is absent or replaced')
        self._carriers(self.original[2:4],publication.original['origin_binding_sha256'])
        _require(publication.original['https_carrier'] is self.original[3],
                 'bound original publication carrier changed')

    def _bind_native_reader(self,loaded,*,carrier,operation_id,lane_id,budget_id,retention_id,origin_binding_sha256):
        self._loaded(loaded)
        _require(self.original is None and self.reader is None,'fresh owner reader invocation required')
        values=(operation_id,lane_id,budget_id,retention_id)
        _require(all(type(x) is str and x for x in values)
                 and loaded.gate.producers.get(values[:2])==values[2:],
                 'reader original operation/lane/resources differ')
        self._carriers((carrier,),origin_binding_sha256)
        self.reader=values
        self.native=OrdinaryPublicationEvidence(self.context,origin_binding_sha256=origin_binding_sha256,
                                               native_reader_carrier=carrier)

    def _bound(self,context):
        self._check()
        gate=context.get('gate')
        _require(gate is not None and gate.evidence.provider is self
                 and gate.repo==self.context.repo and gate.candidate_oid==self.context.candidate_oid
                 and gate.invocation.manifest_digest==self.context.manifest_digest
                 and gate.owner.target.result_path==self.context.result_path
                 and context.get('bootstrap_pid')==self.pid
                 and context.get('original_deadline_monotonic_ns')==self.endpoint
                 and context.get('conversion_result_path')==self.context.result_path
                 and context.get('conversion_manifest_digest')==self.context.manifest_digest,
                 'actual original controller assertion context differs')
        gate._check()  # Assertions are observations inside this actual lease.
        if context.get('lane_id') is not None:
            request=tuple(context.get(k) for k in ('operation_id','lane_id','budget_id','retention_id'))
            expected=self.reader if self.reader is not None else (
                tuple(self.original[4][k] for k in ('operation_id','lane_id','budget_id','retention_id'))
                if self.original is not None else None)
            _require(expected is not None and request==expected,'unbound original controller request')
            live=context.get('native_anchor')
            checked=context.get('native_checked')
            if live is not None:_require(self.original is not None and live.binding is self.original[0],
                                         'foreign actual native anchor')
            if checked is not None:
                _require(self.original is not None and checked.live.binding is self.original[0]
                         and context.get('native_attempt').carrier is self.original[3],
                         'foreign actual publication original')
        else:
            _require((context.get('operation_id'),context.get('budget_id'),context.get('retention_id'))
                     ==(self.context.operation_id,self.context.budget_id,self.context.retention_id),
                     'unbound conversion controller request')
        return gate

    def _assert(self,name,context):
        self._bound(context)
        method=self.loader.callable(getattr(self.authority,name))
        _require(method(**context) is None,'controller assertion returned an admission flag')
        self._check()

    @_sticky_assertion
    def assert_bootstrap_exclusion(self,**context):self._assert('assert_bootstrap_exclusion',context)
    @_sticky_assertion
    def assert_launcher_coverage(self,**context):self._assert('assert_launcher_coverage',context)
    @_sticky_assertion
    def assert_resources(self,**context):self._assert('assert_resources',context)
    @_sticky_assertion
    def assert_process_version(self,**context):self._assert('assert_process_version',context)
    @_sticky_assertion
    def assert_descendants_settled(self,**context):self._assert('assert_descendants_settled',context)
    @_sticky_assertion
    def assert_publication_readback(self,**context):
        self._assert('assert_publication_readback',context)
        native=(context.get('phase') in ('native-anchor-readback','native-reader','native-publication-readback','native-https-readback')
                or any(k in context for k in ('native_anchor','native_reader','native_checked')))
        proof=self.native if native else self.conversion
        _require(proof is not None,'actual bound publication evidence absent')
        return proof.assert_publication_readback(**context)

    def __reduce__(self):raise TypeError('live owner controller cannot transfer')
