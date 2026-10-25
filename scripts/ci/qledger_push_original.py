"""Facts for one fresh ordinary push; no effect or resource admission.

Uses the existing original-result root, one immutable owner record and exact
kernel observations of the supplied shell/its invoking child. Never discovers
writers, initializes a retry, resumes a dead owner or creates a reservation.
"""
from __future__ import annotations

import ctypes
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
from uuid import UUID

# Ordinary file-path imports pin this source tree. In a qualified bootstrap,
# __file__ belongs to the verified outside-checkout bundle; the finite finder
# still refuses every unqualified first-party import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine import qledger_original_result as storage
from scripts.ci.qledger_host_gate import GateRefusal

NAME = 'original-push.json'
SCHEMA = 'qledger.original-push-facts/v1'


def require(condition, message):
    if not condition:
        raise GateRefusal(message)


def _boot():
    if sys.platform == 'darwin':
        # Same existing kernel source used by executive_installed_peer; no
        # service identity, Runtime Job or process census is inferred.
        libc = ctypes.CDLL(None, use_errno=True)
        size = ctypes.c_size_t(128)
        value = ctypes.create_string_buffer(size.value)
        query = libc.sysctlbyname
        query.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        query.restype = ctypes.c_int
        require(query(b'kern.bootsessionuuid', value, ctypes.byref(size), None, 0) == 0, 'kernel boot identity unavailable')
        raw = value.value.decode('ascii')
    elif sys.platform == 'linux':
        raw = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    else:
        raise GateRefusal('kernel process/boot observation unsupported')
    return str(UUID(raw))


def _process(pid):
    require(type(pid) is int and 0 < pid < 2**31, 'explicit original shell PID required')
    if sys.platform == 'darwin':
        # Existing PROC_PIDUNIQIDENTIFIERINFO ABI, also used by Mastermind's
        # executive_process_identity._observe_process_instance. One known PID.
        class Unique(ctypes.Structure):
            _fields_ = [('uuid',ctypes.c_ubyte*16),('unique',ctypes.c_uint64),
                ('parent_unique',ctypes.c_uint64),('version',ctypes.c_int32),
                ('parent_version',ctypes.c_int32),('reserved',ctypes.c_uint64*2)]
        require(ctypes.sizeof(Unique) == 56, 'kernel process ABI unsupported')
        lib = ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
        query = lib.proc_pidinfo
        query.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_uint64,ctypes.c_void_p,ctypes.c_int]
        query.restype = ctypes.c_int
        value = Unique()
        require(query(pid,17,0,ctypes.byref(value),56) == 56 and value.unique > 0 and value.version > 0,
                'original process incarnation unavailable')
        return dict(pid=pid,unique=value.unique,version=value.version,
                    parent_unique=value.parent_unique,parent_version=value.parent_version)
    if sys.platform == 'linux':
        # procfs start ticks are boot-relative; include the boot UUID separately.
        raw = Path(f'/proc/{pid}/stat').read_text()
        tail = raw[raw.rfind(')')+2:].split()
        require(len(tail)>19 and int(tail[19])>0, 'original process incarnation unavailable')
        return dict(pid=pid,start_ticks=int(tail[19]),parent_pid=int(tail[1]))
    raise GateRefusal('kernel process observation unsupported')


def _owner(owner_pid):
    own = _process(owner_pid)
    parent_pid = os.getppid()
    parent = _process(parent_pid)
    if parent_pid != owner_pid:
        # Bash command substitution may add exactly one real child shell.
        if sys.platform == 'darwin':
            require((parent['parent_unique'],parent['parent_version']) == (own['unique'],own['version']),
                    'caller is not the original shell or its direct substitution child')
        else:
            require(parent['parent_pid']==owner_pid, 'caller is not the original shell or its direct substitution child')
    return own


def _origin(repo):
    def read(*args):
        env=dict(os.environ)
        for key in ('GIT_DIR','GIT_WORK_TREE','GIT_COMMON_DIR','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY',
                    'GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_NAMESPACE','GIT_REPLACE_REF_BASE','GIT_SHALLOW_FILE'):
            env.pop(key,None)
        env.update(GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
        with open(os.devnull,'wb') as quiet:
            r=subprocess.run(['git','-C',str(repo),'remote','get-url',*args,'origin'],
                             stdout=subprocess.PIPE,stderr=quiet,env=env,timeout=5)
        require(r.returncode==0 and len(r.stdout)<=4096,'original origin identity unavailable')
        return r.stdout.splitlines()
    fetch,push=read('--all'),read('--push','--all')
    require(len(fetch)==1 and fetch==push and fetch[0], 'original origin is missing or ambiguous')
    return sha256(fetch[0]).hexdigest()


def _inputs(invocation,binding):
    o=invocation.owner
    require(len(binding)==5, 'five exact original publication inputs required')
    require(tuple(binding)==(str(o.target.result_path),invocation.manifest_digest,o.target.accepted_tip_oid,
                            binding[3],binding[4]),'original retained conversion binding differs')
    # Complete candidate/tree must be the exact supplied original publication.
    invocation.preflight(boundary='pre-rebase',candidate_oid=binding[3],tree_oid=binding[4],
                         accepted_tip_oid=o.target.accepted_tip_oid)
    return dict(repo=str(o.repo),result_path=str(o.target.result_path),manifest_digest=invocation.manifest_digest,
                operation_id=o.intent.operation_id,budget_id=o.target.budget_id,retention_id=o.target.retention_id,
                accepted_tip_oid=binding[2],candidate_oid=binding[3],tree_oid=binding[4])


def _budget(deadline,budget,max_attempts,alarm):
    require(all(type(x) is int for x in (deadline,budget,max_attempts,alarm))
            and 0<=budget<2**31 and 0<max_attempts<2**31 and 0<=alarm<2**31 and 0<deadline<2**63,
            'original ordinary retry values invalid')
    return dict(retry_deadline_epoch_seconds=deadline,retry_budget_seconds=budget,
                max_attempts=max_attempts,git_push_alarm_seconds=alarm)


def capture(invocation,*,owner_pid,deadline,budget,max_attempts,alarm,attempt,binding):
    require(attempt==0,'original facts can only be captured at fresh init before attempt one')
    original=_inputs(invocation,binding);contract=_budget(deadline,budget,max_attempts,alarm)
    owner=invocation.owner;boot=_boot();process=_owner(owner_pid)
    # Correlate epoch and monotonic samples without treating a retry-admission
    # deadline as a command/whole-operation deadline. It may already be past;
    # the incumbent's first attempt remains unconditional.
    wall_before=time.time_ns();mono=time.monotonic_ns();wall_after=time.time_ns()
    require(wall_after>=wall_before,'wall clock moved backwards during original capture')
    require(deadline-budget<=wall_before//1_000_000_000,
            'original retry start is in the future')
    origin=_origin(owner.repo)
    root=storage._owner(owner.target.owner_root,owner.target.result_path,owner.target.result_id,owner.claims_path)
    try:
        info=os.fstat(root)
        require(stat.S_IMODE(info.st_mode)==0o700,'original root must already be private')
        doc=dict(schema=SCHEMA,original=original,retry=contract,initial_attempt=0,boot=boot,process=process,
                 origin_binding_sha256=origin,
                 correlation=dict(wall_before_ns=wall_before,wall_after_ns=wall_after,monotonic_ns=mono,
                    retry_start_monotonic_lower_ns=mono+(deadline-budget)*1_000_000_000-wall_after,
                    retry_start_monotonic_upper_ns=mono+(deadline-budget)*1_000_000_000-wall_before,
                    retry_deadline_monotonic_lower_ns=mono+deadline*1_000_000_000-wall_after,
                    retry_deadline_monotonic_upper_ns=mono+deadline*1_000_000_000-wall_before),
                 root=dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,mode=stat.S_IMODE(info.st_mode)),
                 resource_assurance='PRIVATE_ROOT_CUSTODY_ONLY_POLICY_NOT_PROVIDED',
                 timing_assurance='RETRY_ADMISSION_CORRELATION_NOT_A_WHOLE_OPERATION_ENDPOINT')
        require(_boot()==boot and _owner(owner_pid)==process and _origin(owner.repo)==origin,
                'original owner or origin changed during creation')
        raw=storage._json(doc);require(len(raw)<=16384,'original facts exceeded bound')
        storage._write(root,NAME,raw)  # O_EXCL: unknown/existing originals never get replaced.
        os.fsync(root);storage._stable_owner(owner.target.owner_root,root)
        digest=sha256(raw).hexdigest()
    finally:
        os.close(root)
    inspect(invocation,owner_pid=owner_pid,deadline=deadline,budget=budget,max_attempts=max_attempts,
            alarm=alarm,attempt=0,binding=binding,digest=digest)
    return digest


def inspect(invocation,*,owner_pid,deadline,budget,max_attempts,alarm,attempt,binding,digest):
    require(type(digest) is str and len(digest)==64 and all(x in '0123456789abcdef' for x in digest),
            'same original facts digest required; no recapture')
    owner=invocation.owner
    root=storage._owner(owner.target.owner_root,owner.target.result_path,owner.target.result_id,owner.claims_path)
    try:
        info=os.fstat(root);raw=storage._read(root,NAME,16384,[])
        require(sha256(raw).hexdigest()==digest,'same original facts changed or identity is unknown')
        doc=json.loads(raw)
        require(storage._json(doc)==raw and doc['schema']==SCHEMA,'original facts malformed')
        # Inspect after publication may legitimately observe an advanced tracking
        # ref: compare immutable supplied original fields, do not rebase/reprepare.
        original=dict(repo=str(owner.repo),result_path=str(owner.target.result_path),manifest_digest=invocation.manifest_digest,
          operation_id=owner.intent.operation_id,budget_id=owner.target.budget_id,retention_id=owner.target.retention_id,
          accepted_tip_oid=binding[2],candidate_oid=binding[3],tree_oid=binding[4])
        require(tuple(binding[:3])==(str(owner.target.result_path),invocation.manifest_digest,owner.target.accepted_tip_oid)
                and doc['original']==original and doc['retry']==_budget(deadline,budget,max_attempts,alarm),
                'original retry/result inputs changed; no restart budget')
        require(doc['root']==dict(device=info.st_dev,inode=info.st_ino,uid=info.st_uid,mode=stat.S_IMODE(info.st_mode)),
                'original root custody changed')
        require(doc['boot']==_boot() and doc['process']==_owner(owner_pid),'original shell incarnation unavailable; no restart admission')
        require(doc['origin_binding_sha256']==_origin(owner.repo),'original origin changed; no recapture')
        require(type(attempt) is int and 0<=attempt<=max_attempts,'current original attempt count unavailable')
        require(time.monotonic_ns()>=doc['correlation']['monotonic_ns'],'original monotonic clock regressed')
        storage._stable_owner(owner.target.owner_root,root)
    finally:
        os.close(root)
    # This describes the EXISTING loop, never overrides its first-attempt rule.
    return 'exhausted' if attempt>=max_attempts or (attempt>0 and int(time.time())>=deadline) else 'first' if attempt==0 else 'retry'
