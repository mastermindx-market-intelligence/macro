"""Execution-local action composition; same explicit S3 native fixture stand-ins."""
import copy
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
import pytest
from engine.research_factory import market_memory_fitted_factory_use as ffi
from engine.neuralweb import market_memory_retained_use as house
from tests.test_market_memory_fitted_factory_use import (completed_world, fitted_world,
    retained_owner, native_training, selection, records)

ACTION = "read_retained_generation_metadata"

def test_exact_actions_and_direct_scope_keep_two_fresh_boundaries(completed_world, monkeypatch):
    p=completed_world["policy"];before=p._recheck_owner;counts=[]
    def check(): counts.append(1);return before()
    monkeypatch.setattr(p,"_recheck_owner",check)
    def unexpected(*args):pytest.fail("substituted scope dispatch")
    with monkeypatch.context() as m:
        m.setattr(p._training_scope,"check",unexpected)
        p.check(ACTION,dict(p._training_bound))
    assert len(counts)==2
    counts.clear();p._training_scope.check(ACTION,dict(p._training_bound));assert len(counts)==2
    with pytest.raises(ffi.FittedFactoryUseError):
        p._training_scope.check(ACTION,dict(p._query_bound))

def test_frame_copies_context_replay_and_cross_thread_cannot_borrow_exemption(completed_world,monkeypatch):
    p=completed_world["policy"];original=house.load_registration;saved=[]
    def load(*args):
        frame=ffi._ACTION_FRAME.get()
        if frame is not None and not saved:
            saved.append((frame,copy.copy(frame),copy_context()))
            # The intended first principal hook has already consumed issuance.
            with pytest.raises(ffi.FittedFactoryUseError):p._training_scope._enforce_current_principal()
            token=ffi._ACTION_FRAME.set(saved[0][1])
            try:
                with pytest.raises(ffi.FittedFactoryUseError):p._training_scope._enforce_current_principal()
            finally:ffi._ACTION_FRAME.reset(token)
        return original(*args)
    monkeypatch.setattr(house,"load_registration",load)
    p.check(ACTION,dict(p._training_bound))
    frame,clone,ctx=saved[0];assert not frame.active and clone.active
    for value in (frame,clone):
        token=ffi._ACTION_FRAME.set(value)
        try:
            with pytest.raises(ffi.FittedFactoryUseError):p._training_scope._enforce_current_principal()
        finally:ffi._ACTION_FRAME.reset(token)
    with pytest.raises(ffi.FittedFactoryUseError):ctx.run(p._training_scope._enforce_current_principal)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(ffi.FittedFactoryUseError):pool.submit(ctx.run,p._training_scope._enforce_current_principal).result()
    assert ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())

def test_native_refusal_and_final_failure_retire_issuance(completed_world,monkeypatch):
    p=completed_world["policy"];original=house.load_registration
    def denied(*args):
        if ffi._ACTION_FRAME.get() is not None:raise house.RetainedUseError("synthetic_native_refusal")
        return original(*args)
    with monkeypatch.context() as m:
        m.setattr(house,"load_registration",denied)
        with pytest.raises(house.RetainedUseError,match="synthetic_native_refusal"):p.check(ACTION,dict(p._training_bound))
    assert ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())
    before=p._recheck_owner;calls=[]
    def fail_final():
        calls.append(1)
        if len(calls)==2:raise ffi.FittedFactoryUseError("synthetic_final_failure")
        return before()
    with monkeypatch.context() as m:
        m.setattr(p,"_recheck_owner",fail_final)
        with pytest.raises(ffi.FittedFactoryUseError,match="synthetic_final_failure"):p.check(ACTION,dict(p._training_bound))
    assert ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())
    p.check(ACTION,dict(p._training_bound))

def test_next_action_current_registration_revoke_still_refuses(completed_world):
    w=completed_world;p=w["policy"];p.check(ACTION,dict(p._training_bound))
    w["registration_path"].write_bytes(b"{}")
    with pytest.raises(house.RetainedUseError):p.check(ACTION,dict(p._training_bound))

def test_expiry_during_inherited_rights_fails_fresh_final_check(completed_world,monkeypatch):
    w=completed_world;p=w["policy"];original=house.load_registration
    def expire(*args):
        result=original(*args)
        if ffi._ACTION_FRAME.get() is not None:w["now"][0]="2027-01-01T00:00:00.000000Z"
        return result
    monkeypatch.setattr(house,"load_registration",expire)
    with pytest.raises(ValueError):p.check(ACTION,dict(p._training_bound))
    assert ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())


def test_only_actual_issuer_frame_consumes_first_hook(completed_world,monkeypatch):
    p=completed_world["policy"];scope=p._training_scope;original=scope._enforce_current_principal
    observed=[]
    def hook():
        frame=ffi._ACTION_FRAME.get()
        if frame is None:return original()
        for clone in (copy.copy(frame),copy.deepcopy(frame)):
            token=ffi._ACTION_FRAME.set(clone)
            try:
                with pytest.raises(ffi.FittedFactoryUseError):original()
            finally:ffi._ACTION_FRAME.reset(token)
        observed.append(1)
        original()
        with pytest.raises(ffi.FittedFactoryUseError):original()
    monkeypatch.setattr(scope,"_enforce_current_principal",hook)
    p.check(ACTION,dict(p._training_bound))
    assert observed==[1] and ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())


def test_inherited_validator_must_execute_hook_and_complete_synchronously(completed_world,monkeypatch):
    p=completed_world["policy"];original=house.RetainedHouseUsePolicy.check
    with monkeypatch.context() as m:
        m.setattr(house.RetainedHouseUsePolicy,"check",lambda *args:None)
        with pytest.raises(ffi.FittedFactoryUseError,match="not_completed"):p.check(ACTION,dict(p._training_bound))
    def incomplete(*args):
        original(*args)
        return object()
    with monkeypatch.context() as m:
        m.setattr(house.RetainedHouseUsePolicy,"check",incomplete)
        with pytest.raises(ffi.FittedFactoryUseError,match="not_completed"):p.check(ACTION,dict(p._training_bound))
    assert ffi._ACTION_FRAME.get() is None and not getattr(ffi._ISSUERS,"stack",())


def test_original_strict_resource_types_remain_refused(completed_world):
    p=completed_world["policy"]
    class ListSubclass(list):pass
    class StringSubclass(str):pass
    receipt="mmsrc_"+"a"*64
    for refs in ((receipt,),ListSubclass([receipt]),[StringSubclass(receipt)]):
        resource={**p._training_bound,"source_receipt_ids":refs}
        with pytest.raises(house.RetainedUseError,match="original_source_use_not_admitted"):
            p.check(ACTION,resource)
    rich={**p._training_bound,"capture_id":StringSubclass("mmcapture_"+"a"*64),
          "context_id":"mmctx_"+"b"*64,"packet_sha256":"c"*64,"source_receipt_ids":[receipt]}
    with pytest.raises(house.RetainedUseError,match="authenticated_capture_resource_required"):
        p.check("disclose_retained_macro_capture",rich)
