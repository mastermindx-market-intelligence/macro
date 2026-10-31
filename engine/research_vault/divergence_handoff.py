"""Same ordinary nightly invocation handoff. No acquisition or recomputation.

Source preparation only. The future workflow supplies its existing run identity,
private runner artifact carrier and Research credentials at their incumbent step.
Environment declarations are not independent caller/source authentication.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import logging
from dataclasses import dataclass

from engine.research_vault import divergence_capture as retention

REPOSITORY="mastermindx-market-intelligence/macro"
SOURCE_PATHS=("engine/foresight_divergence.py", "engine/research_vault/divergence_capture.py",
    "engine/research_vault/divergence_handoff.py", "engine/research_vault/generation_evidence.py",
    "engine/research_vault/r2_store.py", "scripts/build_foresight.py",
    "scripts/publish_native_divergence_capture.py")
log=logging.getLogger(__name__)

@dataclass(frozen=True)
class NativeContext:
    run_id: str
    commit: str
    repo: Path
    directory: Path
    source_sha256: str

def _head(repo):
    env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","GIT_NO_LAZY_FETCH":"1","GIT_ALLOW_PROTOCOL":""}
    result=subprocess.run(["git","--no-replace-objects","-C",str(repo),"rev-parse","HEAD"],
        env=env,check=True,capture_output=True,timeout=3)
    raw=result.stdout
    if len(raw)>41 or re.fullmatch(rb"[0-9a-f]{40}\n?",raw) is None:
        raise retention.CaptureRefused("native source identity unavailable")
    return raw.decode().strip()

def _source_binding(repo):
    """Committed placement of the narrow executing closure; not memory attestation."""
    commit=_head(repo)
    env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","GIT_NO_LAZY_FETCH":"1","GIT_ALLOW_PROTOCOL":""}
    listing=subprocess.run(["git","--no-replace-objects","-C",str(repo),"ls-tree",commit,"--",*SOURCE_PATHS],
        env=env,check=True,capture_output=True,timeout=3).stdout
    if len(listing)>8192: raise retention.CaptureRefused("source closure unavailable")
    entries={}
    for line in listing.decode().splitlines():
        metadata,path=line.split("\t",1)
        mode,kind,oid=metadata.split()
        if path not in SOURCE_PATHS or kind!="blob" or mode not in {"100644","100755"}:
            raise retention.CaptureRefused("committed source closure required")
        entries[path]=(mode,oid)
    if set(entries)!=set(SOURCE_PATHS): raise retention.CaptureRefused("incomplete source closure")
    digests={}
    for relative,(mode,oid) in entries.items():
        path=repo/relative
        if path.resolve(strict=True)!=path: raise retention.CaptureRefused("source symlink refused")
        with path.open("rb") as stream:
            before=os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size>1048576:
                raise retention.CaptureRefused("bounded source file required")
            raw=stream.read(1048577);after=os.fstat(stream.fileno())
        if len(raw)!=before.st_size or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise retention.CaptureRefused("source changed during read")
        actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if actual!=oid or bool(before.st_mode&0o111)!=(mode=="100755"):
            raise retention.CaptureRefused("source closure differs from committed bytes")
        digests[relative]=retention.digest(raw)
    if _head(repo)!=commit: raise retention.CaptureRefused("source moved during binding")
    return commit,retention.digest(retention.canonical(digests))

def _identity(repo_root,environ):
    # Refuse before filesystem/store creation in every render/non-nightly path.
    if environ.get("RENDER_NO_DRIP")=="1" or environ.get("COLLECT_LANE")!="nightly":
        return None
    if (environ.get("GITHUB_ACTIONS")!="true" or environ.get("GITHUB_REPOSITORY")!=REPOSITORY
        or environ.get("GITHUB_JOB")!="engine"
        or environ.get("GITHUB_WORKFLOW_REF")!=REPOSITORY+"/.github/workflows/daily.yml@refs/heads/main"):
        raise retention.CaptureRefused("original nightly invocation required")
    rid,attempt=environ.get("GITHUB_RUN_ID",""),environ.get("GITHUB_RUN_ATTEMPT","")
    if not all(re.fullmatch(r"[1-9][0-9]{0,19}",x) for x in (rid,attempt)):
        raise retention.CaptureRefused("exact native run and attempt required")
    repo=Path(repo_root).resolve(strict=True)
    temp_raw=environ.get("RUNNER_TEMP","")
    if not temp_raw or not Path(temp_raw).is_absolute():
        raise retention.CaptureRefused("existing runner artifact carrier required")
    temp=Path(temp_raw).resolve(strict=True)
    if temp==repo or temp.is_relative_to(repo):
        raise retention.CaptureRefused("private capture must stay outside checkout")
    run=REPOSITORY+":daily:"+rid+":"+attempt+":engine:build_foresight"
    directory=temp/("native-divergence-"+hashlib.sha256(run.encode()).hexdigest())
    return run,repo,directory

def _private_directory(path):
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
        raise retention.CaptureRefused("private original invocation directory required")

def begin(repo_root,*,environ=None):
    identity=_identity(repo_root,os.environ if environ is None else environ)
    if identity is None:
        return None
    run,repo,directory=identity
    commit,source_sha256=_source_binding(repo)
    # A failed/partial previous invocation is retained, never adopted or erased.
    directory.mkdir(mode=0o700,exist_ok=False)
    _private_directory(directory)
    return NativeContext(run,commit,repo,directory,source_sha256)

def stage(capture,context):
    if type(context) is not NativeContext or _source_binding(context.repo)!=(context.commit,context.source_sha256):
        raise retention.CaptureRefused("source moved during original computation")
    _private_directory(context.directory)
    _key,raw=retention.prepare(capture,native_run_id=context.run_id,producer_commit=context.commit)
    path=context.directory/"capture.json"
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        remaining=memoryview(raw)
        while remaining:
            written=os.write(fd,remaining)
            if written<=0: raise OSError("private staging made no progress")
            remaining=remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    directory=os.open(context.directory,os.O_RDONLY|os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return {"state":"STAGED_PRIVATE_NATIVE_CAPTURE","payload_sha256":retention.digest(raw),"source_sha256":context.source_sha256,"producer_commit":context.commit}

def emit_step_outputs(values,*,environ=None):
    """Existing Actions output channel; fixed names, bounded values, no source body."""
    environ=os.environ if environ is None else environ
    allowed={"native_divergence_payload_sha256","native_divergence_source_sha256","native_divergence_journal","native_divergence_producer_commit"}
    if not values or not set(values)<=allowed:
        raise retention.CaptureRefused("closed native output fields required")
    for key,value in values.items():
        if type(value) is not str or not value or len(value)>2048 or any(ord(c)<32 for c in value):
            raise retention.CaptureRefused("bounded native output value required")
        if key.endswith("sha256") and retention.SHA_RE.fullmatch(value) is None:
            raise retention.CaptureRefused("native output digest required")
        if key.endswith("producer_commit") and retention.COMMIT_RE.fullmatch(value) is None:
            raise retention.CaptureRefused("native output commit required")
    output=Path(environ.get("GITHUB_OUTPUT",""))
    if not output.is_absolute(): raise retention.CaptureRefused("original Actions output channel required")
    fd=os.open(output,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid():
            raise retention.CaptureRefused("original Actions output file required")
        raw="".join(key+"="+value+"\n" for key,value in values.items()).encode()
        if os.write(fd,raw)!=len(raw): raise retention.CaptureRefused("native output append incomplete")
    finally: os.close(fd)

def compute_with_capture(cascade,activity,*,repo_root,compute,environ=None):
    """One incumbent board call; capture failure never triggers recomputation."""
    environ=os.environ if environ is None else environ
    try:
        context=begin(repo_root,environ=environ)
    except Exception as exc:
        log.warning("native divergence capture unavailable before compute: %s",type(exc).__name__)
        context=None
    sink={} if context is not None else None
    kwargs={"write_ledger":True}
    if sink is not None: kwargs.update(provenance_sink=sink,capture_optional=True)
    board=compute(cascade,activity,**kwargs)
    if context is not None:
        try:
            staged=stage(sink,context)
            emit_step_outputs({"native_divergence_payload_sha256":staged["payload_sha256"],
                "native_divergence_source_sha256":staged["source_sha256"],
                "native_divergence_producer_commit":staged["producer_commit"]},environ=environ)
        except Exception as exc:
            log.warning("native divergence capture unavailable after compute: %s",type(exc).__name__)
    return board

def _unique(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise retention.CaptureRefused("duplicate staged field")
        out[key]=value
    return out

def _load_staged(context,expected_payload_sha256):
    path=context.directory/"capture.json"
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_mode&0o077 or before.st_nlink!=1 or not 0<before.st_size<=retention.MAX_BYTES:
            raise retention.CaptureRefused("private bounded staged file required")
        raw=os.pread(fd,before.st_size+1,0)
        after=os.fstat(fd)
        if len(raw)!=before.st_size or (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise retention.CaptureRefused("staged bytes changed during read")
    finally: os.close(fd)
    if retention.digest(raw)!=expected_payload_sha256:
        raise retention.CaptureRefused("original stage digest mismatch")
    def nonfinite(_): raise retention.CaptureRefused("nonfinite staged value")
    envelope=json.loads(raw,object_pairs_hook=_unique,parse_constant=nonfinite)
    if type(envelope) is not dict or envelope.get("native_run_id")!=context.run_id or envelope.get("declared_producer_commit")!=context.commit:
        raise retention.CaptureRefused("staged invocation/source mismatch")
    _key,expected=retention.prepare(envelope.get("capture"),native_run_id=context.run_id,producer_commit=context.commit)
    if raw!=expected:
        raise retention.CaptureRefused("staged envelope differs from exact native capture")
    return envelope["capture"]

def retain_staged(repo_root,*,expected_payload_sha256,expected_source_sha256,original_producer_commit,environ=None):
    identity=_identity(repo_root,os.environ if environ is None else environ)
    if identity is None:
        return None
    if any(type(value) is not str or retention.SHA_RE.fullmatch(value) is None for value in (expected_payload_sha256,expected_source_sha256)):
        raise retention.CaptureRefused("original stage outputs required")
    if type(original_producer_commit) is not str or retention.COMMIT_RE.fullmatch(original_producer_commit) is None:
        raise retention.CaptureRefused("original producer commit required")
    run,repo,directory=identity
    _private_directory(directory)
    commit,source_sha256=_source_binding(repo)
    if commit!=original_producer_commit: raise retention.CaptureRefused("original producer source mismatch")
    if source_sha256!=expected_source_sha256: raise retention.CaptureRefused("original source closure changed")
    context=NativeContext(run,commit,repo,directory,source_sha256)
    capture=_load_staged(context,expected_payload_sha256)
    if _source_binding(repo)!=(commit,source_sha256):
        raise retention.CaptureRefused("source moved before private retention")
    return retention.retain_private_capture(capture,native_run_id=run,
        producer_commit=context.commit,private_run_dir=directory)

def journal_path(repo_root,*,expected_payload_sha256,original_producer_commit,environ=None):
    """Return only the fixed metadata journal; never the staged capture path."""
    identity=_identity(repo_root,os.environ if environ is None else environ)
    if identity is None: return None
    if type(expected_payload_sha256) is not str or retention.SHA_RE.fullmatch(expected_payload_sha256) is None:
        raise retention.CaptureRefused("original stage digest required")
    if type(original_producer_commit) is not str or retention.COMMIT_RE.fullmatch(original_producer_commit) is None:
        raise retention.CaptureRefused("original producer commit required")
    run,_repo,directory=identity
    path=directory/("native-divergence-"+retention.digest(run.encode())+".jsonl")
    if not path.exists(): return None
    _private_directory(directory)
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode&0o077 or info.st_uid!=os.getuid() or info.st_nlink!=1 or not 0<info.st_size<=32768:
        raise retention.CaptureRefused("original journal carrier changed")
    from engine.research_vault.generation_evidence import read_evidence
    events=read_evidence(path,expected_identity={"source_commit":original_producer_commit,"run":run},max_bytes=32768)
    seen=set()
    for event in events[1:]:
        kind,payload=event["kind"],event["payload"]
        if kind not in {"write_intent","terminal"} or kind in seen or "terminal" in seen:
            raise retention.CaptureRefused("closed journal event order required")
        seen.add(kind)
        fields={"key","sha256","bytes","conditional","expected_version","content_type"} if kind=="write_intent" else {"state","write_intent_durable","key","sha256"}
        if set(payload)!=fields or payload["key"]!=retention.key_for_run(run) or payload["sha256"]!=expected_payload_sha256:
            raise retention.CaptureRefused("journal metadata only")
        if kind=="write_intent":
            if type(payload["bytes"]) is not int or not 0<payload["bytes"]<=retention.MAX_BYTES or payload["conditional"] is not True or payload["expected_version"] is not None or payload["content_type"]!="application/json":
                raise retention.CaptureRefused("closed write intent required")
        elif payload["state"] not in {"COMMITTED_OBSERVED","UNRESOLVED"} or payload["write_intent_durable"] is not ("write_intent" in seen):
            raise retention.CaptureRefused("closed terminal metadata required")
    return path
