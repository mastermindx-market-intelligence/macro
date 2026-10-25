"""Opt-in one-original-Git-attempt native publication through an isolated Git control context.

Explicit local origins and an explicitly supplied checkout HTTPS header carrier
are supported. This module supplies no credential, resource authority, installer or retry loop. Control
files reference the incumbent object database; no claims/result store is copied.
"""
from hashlib import sha256
import os
from pathlib import Path
import selectors
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine import qledger_store as store
from engine.qledger_store_sources import _open_directory
from scripts.ci import qledger_conversion_candidate as candidate

_SEAL = object()


# Qualified inline helpers use stdlib only under -I. The original alarm is set
# once by the existing outer exec wrapper and survives exec into this driver.
# Git receives objects directly in the existing origin DB, before the original owner performs the descriptor-bound
# standard loose-ref lock/CAS. No receive-pack repository rediscovery or shadow ref/store.
_LOCAL_UPDATE = r'''import os,stat,subprocess,sys
origin_fd,control_fd=int(sys.argv[1]),int(sys.argv[2])
git,oid,old,upload=sys.argv[3:]
os.fchdir(origin_fd)
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
env.update(GIT_DIR='.',GIT_COMMON_DIR='.',GIT_CONFIG_NOSYSTEM='1',
 GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0',
 GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1')
base=[git,'--git-dir=.','--bare','-c','gc.auto=0','-c','maintenance.auto=false',
 '-c','protocol.allow=never','-c','protocol.file.allow=always']
def inspect(args):
 child=subprocess.Popen(base+args,env=env,stdin=subprocess.DEVNULL,
  stdout=subprocess.PIPE,stderr=sys.stderr)
 data=child.stdout.read(4097)
 if len(data)>4096:raise RuntimeError('original local policy exceeds bound')
 child.stdout.close()
 return child.wait(),data
rc,bare=inspect(['config','--local','--get','core.bare'])
if rc!=0 or bare!=b'true\n':raise RuntimeError('only explicit bare local origins supported')
rc,hooks=inspect(['config','--local','--get-all','core.hooksPath'])
if rc!=1 or hooks:raise RuntimeError('receive-hook policy requires admitted transport')
# This mechanism cannot promise receive-pack hook semantics. Refuse enabled
# hooks before object/ref effects, even when a hook would appear permissive.
try:hooks_fd=os.open('hooks',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
except FileNotFoundError:hooks_fd=None
if hooks_fd is not None:
 try:
  names=os.listdir(hooks_fd)
  if len(names)>128:raise RuntimeError('original hook inventory exceeds bound')
  for name in names:
   if not name.endswith('.sample'):
    info=os.stat(name,dir_fd=hooks_fd,follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_mode&0o111:
     raise RuntimeError('receive-hook policy requires admitted transport')
 finally:os.close(hooks_fd)
try:alternate=os.open('objects/info/alternates',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
except FileNotFoundError:alternate=None
if alternate is not None:
 os.close(alternate);raise RuntimeError('destination object alternates require separate admitted custody')
rc=subprocess.call(base+['fetch','--quiet','--no-write-fetch-head','--no-tags',
 '--no-recurse-submodules','--no-auto-maintenance','--upload-pack='+upload,
 'qledger-original',oid],env=env,stdin=subprocess.DEVNULL,stdout=sys.stderr,
 stderr=sys.stderr,pass_fds=(control_fd,))
if rc:sys.exit(rc)
sys.stdout.write('objects-ready\n')
'''


_PRIMARY_CUSTODY = r'''import hashlib,os,re,stat,struct,subprocess,sys,zlib
objects_fd=int(sys.argv[1]);git,control=sys.argv[2:4]
count,max_size,total_size=map(int,sys.argv[4:7])
object_budget=int(sys.argv[7]) if len(sys.argv)>7 else count
payload=sys.stdin.buffer.read(count*41+1)
if len(payload)!=count*41:raise RuntimeError('incomplete original object inventory')
wanted=set(payload.decode('ascii').splitlines())
if len(wanted)!=count or any(len(x)!=40 or any(c not in '0123456789abcdef' for c in x) for x in wanted):
 raise RuntimeError('invalid original object inventory')
os.fchdir(objects_fd)
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
env.update(GIT_DIR=control,GIT_COMMON_DIR=control,GIT_OBJECT_DIRECTORY='.',
 GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_GLOBAL=os.devnull,
 GIT_CONFIG_COUNT='0',GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1')
# Physical paths must belong to this primary namespace, not merely resolve to
# the right bytes. All traversal is relative to the opened primary directory.
physical={}
def identity(info):
 return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
def opened(name,directory=False):
 parts=name.split('/') if name!='.' else []
 parent=os.dup(objects_fd)
 try:
  for part in parts[:-1]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
   os.close(parent);parent=child
  if not parts:return parent
  child=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_DIRECTORY if directory else 0),dir_fd=parent)
  os.close(parent);return child
 except BaseException:
  os.close(parent);raise
def remember(name,fd,directory=False):
 info=os.fstat(fd)
 if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
  raise RuntimeError('physical primary object path is not regular')
 value=identity(info)
 if name in physical and physical[name]!=(directory,value):raise RuntimeError('physical primary object changed')
 physical[name]=(directory,value)
 return info
def finish(name,fd):
 os.fsync(fd)
 if identity(os.fstat(fd))!=physical[name][1]:raise RuntimeError('physical primary bytes changed during verification')
def recheck_physical():
 for name,(directory,value) in physical.items():
  fd=opened(name,directory)
  try:
   if identity(os.fstat(fd))!=value:raise RuntimeError('physical primary namespace changed before CAS')
  finally:os.close(fd)
def loose(name,oid):
 fd=opened(name);remember(name,fd)
 try:
  decoder=zlib.decompressobj();digest=hashlib.sha1();header=bytearray();size=None;length=0
  def consume(out):
   nonlocal size,length
   if size is None:
    header.extend(out);end=header.find(0)
    if end<0:
     if len(header)>64:raise RuntimeError('invalid physical loose header')
     return
    head=bytes(header[:end]);fields=head.split(b' ')
    if len(fields)!=2 or fields[0] not in (b'blob',b'tree',b'commit',b'tag') or not fields[1].isdigit():
     raise RuntimeError('invalid physical loose header')
    size=int(fields[1])
    if size>max_size or head!=fields[0]+b' '+str(size).encode():raise RuntimeError('physical loose size exceeds original')
    digest.update(head+b'\0');out=bytes(header[end+1:]);header.clear()
   length+=len(out)
   if length>size:raise RuntimeError('physical loose object exceeds original')
   digest.update(out)
  while True:
   block=os.read(fd,65536)
   if not block:break
   if decoder.eof:raise RuntimeError('trailing physical loose bytes')
   pending=block
   while pending:
    out=decoder.decompress(pending,65536);tail=decoder.unconsumed_tail;consume(out)
    if decoder.eof:
     if decoder.unused_data or tail:raise RuntimeError('trailing physical loose bytes')
     break
    if tail==pending and not out:raise RuntimeError('physical loose decoder made no progress')
    pending=tail
  while not decoder.eof:
   out=decoder.decompress(b'',65536)
   if not out:break
   consume(out)
  if not decoder.eof or size is None or length!=size or digest.hexdigest()!=oid:
   raise RuntimeError('physical primary object does not match exact original inventory')
  finish(name,fd)
  return size
 finally:os.close(fd)
for directory in ('.','info','pack'):
 fd=opened(directory,True)
 try:remember(directory,fd,True)
 finally:os.close(fd)
for name in ('info/alternates','info/http-alternates'):
 try:fd=opened(name)
 except FileNotFoundError:continue
 else:
  os.close(fd);raise RuntimeError('physical primary object indirection is unsupported')
root_names=os.listdir(objects_fd)
if len(root_names)>object_budget+258:raise RuntimeError('physical primary inventory exceeds bound')
loose_names={};entry_count=0
for directory in root_names:
 if directory in ('info','pack'):continue
 if not re.fullmatch('[0-9a-f]{2}',directory):raise RuntimeError('unqualified physical primary directory')
 fd=opened(directory,True)
 try:
  remember(directory,fd,True);names=os.listdir(fd)
  entry_count+=len(names)
  if entry_count>object_budget:raise RuntimeError('physical primary inventory exceeds bound')
  for name in names:
   if not re.fullmatch('[0-9a-f]{38}',name):raise RuntimeError('unqualified physical loose pathname')
   info=os.stat(name,dir_fd=fd,follow_symlinks=False)
   if not stat.S_ISREG(info.st_mode):raise RuntimeError('physical primary loose object is not regular')
   loose_names[directory+name]=directory+'/'+name
 finally:os.close(fd)
loose_bytes=0
for oid in tuple(wanted):
 if oid in loose_names:
  loose_bytes+=loose(loose_names[oid],oid);wanted.remove(oid)
if loose_bytes>total_size:raise RuntimeError('physical loose bytes exceed exact original')
total_size-=loose_bytes
pack_dir=opened('pack',True)
try:pack_names=os.listdir(pack_dir)
finally:os.close(pack_dir)
if len(pack_names)>object_budget*8+1:raise RuntimeError('physical pack inventory exceeds bound')
for name in pack_names:
 fd=opened('pack/'+name)
 try:remember('pack/'+name,fd)
 finally:os.close(fd)
packed=set()
for name in pack_names:
 if not name.endswith('.idx'):continue
 if not re.fullmatch('pack-[0-9a-f]{40}\.idx',name):raise RuntimeError('unqualified primary pack index')
 relative='pack/'+name;fd=opened(relative)
 try:
  info=remember(relative,fd)
  if info.st_size>object_budget*40+4096:raise RuntimeError('primary index exceeds existing object budget')
  data=bytearray()
  while len(data)<=info.st_size:
   part=os.read(fd,min(65536,info.st_size+1-len(data)))
   if not part:break
   data.extend(part)
  if len(data)!=info.st_size or len(data)<1064 or hashlib.sha1(data[:-20]).digest()!=data[-20:]:
   raise RuntimeError('physical primary index checksum differs')
  v2=data[:4]==b'\xfftOc';offset=8 if v2 else 0
  if v2 and bytes(data[4:8])!=struct.pack('!I',2):raise RuntimeError('unsupported physical index version')
  fanout=struct.unpack('!256I',data[offset:offset+1024]);n=fanout[-1]
  if n>object_budget or any(a>b for a,b in zip(fanout,fanout[1:])):raise RuntimeError('invalid physical index count')
  base=offset+1024;minimum=base+n*(28 if v2 else 24)+40
  if len(data)<minimum or (len(data)-minimum)%(8 if v2 else 1) or (not v2 and len(data)!=minimum):
   raise RuntimeError('invalid physical primary index layout')
  ids=[bytes(data[base+i*20:base+(i+1)*20]).hex() if v2 else bytes(data[base+i*24+4:base+(i+1)*24]).hex() for i in range(n)]
  if ids!=sorted(set(ids)):raise RuntimeError('invalid physical primary index identities')
  candidates=wanted.intersection(ids)
  if candidates:
   pack_name=name[:-4]+'.pack'
   if pack_name not in pack_names:raise RuntimeError('physical primary pack absent')
   pack_fd=opened('pack/'+pack_name)
   try:
    pack_info=remember('pack/'+pack_name,pack_fd);hashed=hashlib.sha1();tail=bytearray();prefix=bytearray();read=0
    while True:
     part=os.read(pack_fd,65536)
     if not part:break
     read+=len(part)
     if len(prefix)<12:prefix.extend(part[:12-len(prefix)])
     tail.extend(part)
     if len(tail)>20:hashed.update(tail[:-20]);del tail[:-20]
    if read!=pack_info.st_size or bytes(prefix[:4])!=b'PACK' or len(prefix)!=12 or struct.unpack('!I',prefix[8:12])[0]!=n:
     raise RuntimeError('physical primary pack inventory differs')
    if len(tail)!=20 or hashed.digest()!=tail or bytes(tail)!=bytes(data[-40:-20]) or tail.hex()!=pack_name[5:-5]:
     raise RuntimeError('physical primary pack checksum differs')
    finish('pack/'+pack_name,pack_fd)
   finally:os.close(pack_fd)
   packed.update(candidates)
  finish(relative,fd)
 finally:os.close(fd)
if not wanted.issubset(packed):raise RuntimeError('required objects have no physical primary custody')
for name,(directory,_) in physical.items():
 if directory:
  fd=opened(name,True)
  try:finish(name,fd)
  finally:os.close(fd)
if not wanted:
 if total_size:raise RuntimeError('physical object aggregate differs')
 recheck_physical();sys.stdout.write('primary-custody-ready\n');sys.exit(0)
count=len(wanted);payload=('\n'.join(sorted(wanted))+'\n').encode()
# --local omits alternate-backed objects, even when readable. Object-directory
# cwd is the opened primary DB; no origin/common-dir/ref discovery occurs.
child=subprocess.Popen([git,'--git-dir='+control,'--bare','pack-objects',
 '--stdout','--local','--window=0','--depth=0','--compression=0',
 '--no-reuse-delta','--no-reuse-object','--no-use-bitmap-index'],
 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=sys.stderr,env=env)
child.stdin.write(payload);child.stdin.close()
buffer=bytearray();pack_hash=hashlib.sha1()
def peek():
 if not buffer:
  part=child.stdout.read(65536)
  if not part:raise RuntimeError('primary object stream incomplete')
  buffer.extend(part)
 return bytes(buffer)
def take(n,hashed=True):
 data=bytearray()
 while len(data)<n:
  peek();k=min(n-len(data),len(buffer));data.extend(buffer[:k]);del buffer[:k]
 if hashed:pack_hash.update(data)
 return bytes(data)
header=take(12)
if header[:4]!=b'PACK' or struct.unpack('!I',header[4:8])[0] not in (2,3):
 raise RuntimeError('invalid primary object stream')
n=struct.unpack('!I',header[8:12])[0]
if n!=count:raise RuntimeError('candidate objects are not held in primary destination')
read_total=0
for _ in range(n):
 byte=take(1)[0];kind=(byte>>4)&7;size=byte&15;shift=4
 while byte&128:
  byte=take(1)[0];size|=(byte&127)<<shift;shift+=7
  if shift>63:raise RuntimeError('invalid primary object size')
 names={1:'commit',2:'tree',3:'blob',4:'tag'}
 if kind not in names or size>max_size or read_total+size>total_size:
  raise RuntimeError('primary object exceeds exact original metadata')
 digest=hashlib.sha1((names[kind]+' '+str(size)+'\0').encode());decoder=zlib.decompressobj();length=0
 while not decoder.eof:
  chunk=peek();out=decoder.decompress(chunk,65536)
  used=len(chunk)-(len(decoder.unused_data) if decoder.eof else len(decoder.unconsumed_tail))
  if used:take(used)
  if not used and not out:raise RuntimeError('primary object decoder made no progress')
  length+=len(out)
  if length>size:raise RuntimeError('primary object size changed')
  digest.update(out)
 if length!=size:raise RuntimeError('primary object is truncated')
 oid=digest.hexdigest()
 if oid not in wanted:raise RuntimeError('primary object does not match exact original inventory')
 wanted.remove(oid);read_total+=length
expected=pack_hash.digest()
if take(20,False)!=expected or wanted or read_total!=total_size:
 raise RuntimeError('primary object custody checksum differs')
if buffer or child.stdout.read(1) or child.wait()!=0:raise RuntimeError('primary object verification incomplete')
recheck_physical()
sys.stdout.write('primary-custody-ready\n')
'''


def require(value, message):
    if not value:
        from engine.qledger_store_protocol import SnapshotIntegrityError
        raise SnapshotIntegrityError('NATIVE_PUBLICATION_UNPROVEN', message)


def _inode(info):
    return info.st_dev, info.st_ino


class NativePublishedGeneration:
    """Explicit immutable reader handoff, never ambient binding replacement."""
    def __init__(self, attempt, seal):
        require(seal is _SEAL and attempt.remote_confirmed, 'actual original remote readback required')
        self._attempt, self.candidate_oid, self.reader_result = attempt, attempt.prepared.candidate_oid, None

    def invoke_reader(self, consumer):
        a = self._attempt
        try:
            a.check()
            require(a.remote_confirmed and not a.uncertain, 'original publication unresolved')
            loader = globals().get('__loader__')
            if getattr(loader, '_qledger_bootstrap_active', False):
                loader.callable(consumer)
            a.readback(self.candidate_oid)
            retained = a.checked.invocation._original()
            binding = store.NativeGitClaimsBinding(a.repo, commit_oid=self.candidate_oid,
                expected_root_digest=retained.write.plan.snapshot.receipt.root_digest, limits=a.checked.invocation.binding.limits)
            # The live owner binding remains selected. An immutable reader is
            # passed explicitly; no ambient scope is cleared or overwritten.
            result = consumer(binding)
            a.check()
            a.readback(self.candidate_oid)
            return result
        except BaseException as exc:
            a.uncertain = True
            a.checked.failure = exc
            raise

    def __reduce__(self):
        raise TypeError('native publication handoff cannot transfer')


class _OriginalPublicationAttempt:
    def __init__(self, checked, prepared, *, origin_binding_sha256, original_origin_inode,
                 original_attempt, original_max_attempts, original_alarm_seconds):
        self.checked, self.prepared, self.pid = checked, prepared, os.getpid()
        self.repo = checked.invocation.binding.repo_root
        self.origin_digest, self.origin_inode = origin_binding_sha256, original_origin_inode
        self.ordinal, self.maximum, self.alarm = original_attempt, original_max_attempts, original_alarm_seconds
        require(type(self.origin_digest) is str and len(self.origin_digest) == 64
                and all(c in '0123456789abcdef' for c in self.origin_digest), 'original origin binding absent')
        require((type(self) is _HTTPSPublicationAttempt and self.origin_inode is None)
                or (type(self.origin_inode) is tuple and len(self.origin_inode) == 2
                    and all(type(x) is int and x >= 0 for x in self.origin_inode)), 'original origin incarnation absent')
        require(all(type(x) is int for x in (self.ordinal,self.maximum,self.alarm))
                and 1 <= self.ordinal <= self.maximum < 2**31 and 0 <= self.alarm < 2**31,
                'actual original ordinal/max/alarm required; no retry initialization')
        self.git = shutil.which('git')
        require(self.git is not None, 'incumbent Git executable unavailable')
        self.origin = self.control = None
        self.origin_fd = self.control_fd = self.objects_fd = None
        self.origin_refs_fd = self.origin_heads_fd = self.origin_lock_fd = None
        self.origin_objects_fd = self.origin_info_fd = self.origin_pack_fd = None
        self.verification_process = None
        self.required_objects = None
        self.origin_ref_before = None
        self.origin_ref_installed = False
        self.alarm_started_ns = None
        self.control_identity = None
        self.objects_path = None
        self.created = {}
        self.directories = {}
        self.process = self.push_process = None
        self.output_buffers = self.last_response = self.push_response = None
        self.effect_started = self.remote_confirmed = self.confirmed = self.uncertain = False
        self._seal = _SEAL

    def check(self, *, full=False):
        require(os.getpid() == self.pid, 'original publication process differs')
        self.checked._check()
        require(self.checked.prepared is self.prepared, 'latest exact full candidate required')
        if full:self.checked.invocation.check(self.prepared,
            push_args=('origin',self.prepared.candidate_oid+':refs/heads/main'))
        if self.origin_fd is not None:
            require(_inode(os.fstat(self.origin_fd)) == self.origin_inode
                    == _inode(os.stat(self.origin,follow_symlinks=False)), 'original origin path/descriptor changed')
        if self.alarm_started_ns is not None and self.alarm:
            require(time.monotonic_ns() < self.alarm_started_ns + self.alarm*1_000_000_000,
                    'unchanged original attempt alarm exhausted')
        if self.origin_refs_fd is not None:
            require(_inode(os.fstat(self.origin_refs_fd)) == _inode(os.stat('refs',dir_fd=self.origin_fd,follow_symlinks=False))
                    and _inode(os.fstat(self.origin_heads_fd)) == _inode(os.stat('heads',dir_fd=self.origin_refs_fd,follow_symlinks=False)),
                    'original ref namespace directory changed')
        if self.origin_objects_fd is not None:
            require(_inode(os.fstat(self.origin_objects_fd))==_inode(os.stat('objects',dir_fd=self.origin_fd,follow_symlinks=False))
                    and _inode(os.fstat(self.origin_info_fd))==_inode(os.stat('info',dir_fd=self.origin_objects_fd,follow_symlinks=False))
                    and _inode(os.fstat(self.origin_pack_fd))==_inode(os.stat('pack',dir_fd=self.origin_objects_fd,follow_symlinks=False)),
                    'destination primary object namespace changed')
        if self.objects_fd is not None:
            require(_inode(os.fstat(self.objects_fd)) == _inode(os.stat(self.objects_path,follow_symlinks=False)),
                    'incumbent object database path/descriptor changed')
        if self.control_fd is not None:
            require(_inode(os.fstat(self.control_fd)) == self.control_identity
                    == _inode(os.stat(self.control,follow_symlinks=False)), 'owned Git control path/descriptor changed')
            self.check_control_inventory()

    def authority(self, method, phase):
        live = self.checked.live
        evidence = getattr(live.gate,'evidence',None)
        assertion = getattr(evidence,method,None)
        require(callable(assertion), 'actual original publication authority unavailable')
        context = dict(gate=live.gate,repo=self.repo,commit_oid=live.installed,
            operation_id=live.binding.operation_id,lane_id=live.binding.lane_id,
            budget_id=live.budget,retention_id=live.retention,phase=phase,
            publication_candidate_oid=self.prepared.candidate_oid,publication_tree_oid=self.prepared.tree_oid,
            original_manifest_digest=self.checked.invocation.manifest_digest,
            original_origin_inode=self.origin_inode,origin_binding_sha256=self.origin_digest,
            original_attempt=self.ordinal,original_max_attempts=self.maximum,original_alarm_seconds=self.alarm,
            git_executable=self.git,publication_transport='local_objects_and_loose_ref_cas',git_pid=self.push_process.pid if self.push_process is not None else None,
            verification_pid=self.verification_process.pid if self.verification_process is not None else None,
            native_checked=self.checked,native_prepared=self.prepared,native_attempt=self)
        from scripts.ci.qledger_owner_invocation import publication_assertion_scope
        with publication_assertion_scope(self, method):
            require(assertion(**context) is None, 'authority returned an admission flag')
        self.check()  # Caught evidence failure cannot rehabilitate this original.

    def origin_bytes(self):
        values=[]
        for args in (['remote','get-url','--all','origin'],['remote','get-url','--push','--all','origin']):
            raw,_=candidate.publication._git(self.repo,args,output_limit=4096)
            values.append(raw.splitlines())
        require(len(values[0])==1 and values[0]==values[1]
                and sha256(values[0][0]).hexdigest()==self.origin_digest,'original logical origin changed')
        return values[0][0]

    def _file(self, relative, payload):
        parent, _, name = relative.rpartition('/')
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,
                   dir_fd=self.directories[parent])
        try:
            count=0
            while count<len(payload):count+=os.write(fd,payload[count:])
            os.fsync(fd)
            self.created[relative]=(_inode(os.fstat(fd)),sha256(payload).hexdigest(),len(payload))
        finally:os.close(fd)

    def setup(self):
        self.check(full=True)
        raw=self.origin_bytes()
        require(raw.startswith(b'/') and b'\0' not in raw,
                'admitted authenticated network transport unavailable; explicit local origin required')
        self.origin=Path(os.fsdecode(raw))
        self.origin_fd=_open_directory(self.origin)
        require(_inode(os.fstat(self.origin_fd))==self.origin_inode,'original origin incarnation changed')
        self.origin_refs_fd=os.open('refs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.origin_fd)
        self.origin_heads_fd=os.open('heads',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.origin_refs_fd)
        self.authority('assert_resources','native-publication-intent')
        self.authority('assert_process_version','native-publication-intent')
        self.origin_objects_fd=os.open('objects',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.origin_fd)
        self.origin_info_fd=os.open('info',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.origin_objects_fd)
        self.origin_pack_fd=os.open('pack',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.origin_objects_fd)
        self.required_objects=candidate.publication._reachable_metadata(self.repo,(self.prepared.candidate_oid,),(),
            limits=self.checked.invocation.binding.limits)
        root=self.checked.invocation._original().owner_root
        self.control=Path(tempfile.mkdtemp(prefix='.qledger-git-control-',dir=root))
        self.control_fd=_open_directory(self.control);self.control_identity=_inode(os.fstat(self.control_fd))
        # Only protocol/config/alternates metadata lives here. Actual objects
        # remain in the incumbent Git DB; receive-pack uses its own remote DB.
        self.directories['']=self.control_fd
        for name in ('refs','objects','objects/info','objects/pack'):
            parent,_,leaf=name.rpartition('/')
            os.mkdir(leaf,mode=0o700,dir_fd=self.directories[parent])
            self.directories[name]=os.open(leaf,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,
                                           dir_fd=self.directories[parent])
        raw,_=candidate.publication._git(self.repo,['rev-parse','--git-path','objects'],output_limit=4096)
        objects=Path(os.fsdecode(raw.rstrip(b'\n')))
        if not objects.is_absolute():objects=self.repo/objects
        self.objects_fd=_open_directory(objects);self.objects_path=objects
        self._file('HEAD',b'ref: refs/heads/unused\n')
        self._file('config',('[core]\n bare = true\n repositoryformatversion = 0\n[remote "origin"]\n url = qledger-original\n').encode())
        self._file('objects/info/alternates',(str(self.objects_path)+'\n').encode())
        raw,_=candidate.publication._git(self.repo,['rev-parse','--git-path','shallow'],output_limit=4096)
        shallow=Path(os.fsdecode(raw.rstrip(b'\n')))
        if not shallow.is_absolute():shallow=self.repo/shallow
        if shallow.exists():
            fd=os.open(shallow,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:payload=os.read(fd,1048577)
            finally:os.close(fd)
            require(len(payload)<=1048576 and all(len(x)==40 and all(c in b'0123456789abcdef' for c in x) for x in payload.splitlines()),'unqualified shallow metadata')
            self._file('shallow',payload)
        self.check()

    def run_git(self,args,*,effect=False):
        # Full immutable candidate/retained chain validation immediately before
        # the actual effect; live root/index/lease/descriptor checks surround
        # every protocol operation without restarting the existing source clock.
        self.check(full=effect)
        if not effect:
            require(args==['rev-parse','--verify','refs/heads/main'],'only exact original ref readback supported')
            raw,_=self.original_ref()
            self.last_response=(raw,b'',0)
            return raw
        self.uncertain=True
        self.effect_started=True
        require(self.origin_lock_fd is None,'original ref transaction already entered')
        self.alarm_started_ns=time.monotonic_ns()
        self.origin_lock_fd=os.open('main.lock',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,
                                    dir_fd=self.origin_heads_fd)
        before,identity=self.original_ref()
        require(before==(self.prepared.accepted_tip_oid+'\n').encode(),'original loose ref CAS changed before ingestion')
        self.origin_ref_before=identity
        os.fchmod(self.origin_lock_fd,identity[1])
        env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        env.update(HOME=str(self.control),XDG_CONFIG_HOME=str(self.control),GIT_CONFIG_NOSYSTEM='1',
            GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0',
            GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1')
        if effect:
            upload_helper='import os,sys;fd=int(sys.argv[1]);git=sys.argv[2];assert sys.argv[3:]==["qledger-original"];os.fchdir(fd);os.environ["GIT_DIR"]=".";os.environ["GIT_COMMON_DIR"]=".";os.execv(git,[git,"--git-dir=.","--bare","upload-pack","--strict","."])'
            upload=shlex.join([sys.executable,'-I','-c',upload_helper,str(self.control_fd),self.git])
            command=[sys.executable,'-I','-c',_LOCAL_UPDATE,str(self.origin_fd),str(self.control_fd),
                     self.git,self.prepared.candidate_oid,self.prepared.accepted_tip_oid,upload]
        else:
            env.update(GIT_DIR='.',GIT_COMMON_DIR='.')
            command=[self.git,'--git-dir=.','--bare',*args]
        # Pin cwd by descriptor before Git resolves its config/common-dir; a
        # renamed control path cannot substitute another invocation's config.
        command=[sys.executable,'-I','-c',
                 'import os,signal,sys;os.fchdir(int(sys.argv[1]));signal.alarm(int(sys.argv[2]));os.execv(sys.argv[3],sys.argv[3:])',
                 str(self.control_fd if effect else self.origin_fd),str(self.alarm if effect else 0),*command]
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            env=env,pass_fds=(self.origin_fd,self.control_fd,self.objects_fd))
        self.process=child
        if effect:self.push_process=child
        data=self.wait_output(child)
        self.last_response=(data,bytes(self.output_buffers[child.stderr]),child.returncode)
        if effect:self.push_response=self.last_response
        require(child.returncode==0,'original Git completion unproven; no retry or guessed cleanup')
        self.uncertain=self.effect_started and not self.remote_confirmed
        return data

    def wait_output(self,child):
        buffers={child.stdout:bytearray(),child.stderr:bytearray()}
        self.output_buffers=buffers
        with selectors.DefaultSelector() as selector:
            for stream in buffers:selector.register(stream,selectors.EVENT_READ)
            while selector.get_map():
                ready=selector.select(self.checked._deadline())
                require(ready,'original response deadline exhausted; original process retained')
                for key,_ in ready:
                    part=os.read(key.fd,min(65536,16385-len(buffers[key.fileobj])))
                    if part:buffers[key.fileobj].extend(part)
                    require(len(buffers[key.fileobj])<=16384,'original Git response exceeds bound; process retained')
                    if not part:selector.unregister(key.fileobj)
            child.wait(timeout=self.checked._deadline())
        for stream in buffers:stream.close()
        return bytes(buffers[child.stdout])

    def original_ref(self):
        # A files-ref backend may ignore GIT_COMMON_DIR. Never ask it to resolve
        # this mutable origin. Only a direct regular loose main ref is supported.
        try:fd=os.open('main',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.origin_heads_fd)
        except FileNotFoundError:
            require(False,'original direct loose main ref required; packed refs unsupported')
        try:
            info=os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size==41,
                    'original direct loose main ref required; packed/symbolic refs unsupported')
            raw=os.read(fd,42)
            require(len(raw)==41 and raw[-1:]==b'\n' and all(c in b'0123456789abcdef' for c in raw[:-1]),
                    'original direct loose main ref required')
            return raw,(_inode(info),stat.S_IMODE(info.st_mode))
        finally:os.close(fd)

    def verify_primary_objects(self):
        self.check()
        rows=self.required_objects
        require(rows,'complete original object inventory required')
        payload=('\n'.join(row[0] for row in rows)+'\n').encode()
        alarm=0
        if self.alarm:
            alarm=(self.alarm_started_ns+self.alarm*1_000_000_000-time.monotonic_ns())//1_000_000_000
            require(alarm>0,'unchanged original attempt alarm exhausted')
        command=[sys.executable,'-I','-c',
            'import os,signal,sys;signal.alarm(int(sys.argv[1]));os.execv(sys.argv[2],sys.argv[2:])',
            str(alarm),sys.executable,'-I','-c',_PRIMARY_CUSTODY,str(self.origin_objects_fd),
            self.git,str(self.control),str(len(rows)),str(max(row[2] for row in rows)),str(sum(row[2] for row in rows)),str(self.checked.invocation.binding.limits.publication_objects)]
        child=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            pass_fds=(self.origin_objects_fd,))
        self.process=self.verification_process=child
        os.set_blocking(child.stdin.fileno(),False)
        sent=0
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdin,selectors.EVENT_WRITE)
            while sent<len(payload):
                require(selector.select(self.checked._deadline()),'original inventory input deadline exhausted')
                sent+=os.write(child.stdin.fileno(),payload[sent:sent+65536])
        child.stdin.close()
        output=self.wait_output(child)
        self.last_response=(output,bytes(self.output_buffers[child.stderr]),child.returncode)
        require(child.returncode==0 and output==b'primary-custody-ready\n',
                'complete candidate object custody in primary destination unproven')
        self.check()

    def commit_original_ref(self):
        self.check(full=True)
        self.verify_primary_objects()
        raw,identity=self.original_ref()
        require(identity==self.origin_ref_before and raw==(self.prepared.accepted_tip_oid+'\n').encode(),
                'original loose ref changed while its standard Git lock was held')
        require(_inode(os.fstat(self.origin_lock_fd))==_inode(os.stat('main.lock',dir_fd=self.origin_heads_fd,follow_symlinks=False)),
                'original ref lock replaced; preserved')
        payload=(self.prepared.candidate_oid+'\n').encode()
        count=0
        while count<len(payload):count+=os.write(self.origin_lock_fd,payload[count:])
        os.fsync(self.origin_lock_fd)
        self.check()
        require(_inode(os.fstat(self.origin_lock_fd))==_inode(os.stat('main.lock',dir_fd=self.origin_heads_fd,follow_symlinks=False)),
                'original ref lock replaced before commit; preserved')
        os.replace('main.lock','main',src_dir_fd=self.origin_heads_fd,dst_dir_fd=self.origin_heads_fd)
        self.origin_ref_installed=True
        os.fsync(self.origin_heads_fd)
        self.check()

    def readback(self,oid):
        raw=self.run_git(['rev-parse','--verify','refs/heads/main'])
        require(raw==(oid+'\n').encode(),'exact original-origin full candidate not confirmed')
        self.check()

    def perform(self,reader):
        self.setup()
        self.readback(self.prepared.accepted_tip_oid)
        output=self.run_git(['push','--porcelain','--force-with-lease=refs/heads/main:'+self.prepared.accepted_tip_oid,
                             'origin',self.prepared.candidate_oid+':refs/heads/main'],effect=True)
        # Object ingestion is not publication. The original owner must complete
        # its exact loose-ref CAS and directory durability before readback.
        require(output==b'objects-ready\n','original object ingestion completion unproven')
        self.commit_original_ref()
        self.readback(self.prepared.candidate_oid)
        self.origin_bytes();self.check(full=True)
        self.authority('assert_publication_readback','native-publication-readback')
        self.authority('assert_descendants_settled','native-publication-readback')
        self.remote_confirmed=True;self.uncertain=False
        generation=NativePublishedGeneration(self,_SEAL)
        if reader is not None:generation.reader_result=generation.invoke_reader(reader)
        self.check();self.confirmed=True
        return generation

    def close_known(self):
        if self.uncertain:return
        # Descriptor-relative owned inventory only. Never traverse a replaced
        # control pathname, recursively delete or clean an uncertain operation.
        if self.control_fd is not None:
            self.check_control()
            self.check_control_inventory()
            for name in self.created:
                parent,_,leaf=name.rpartition('/')
                os.unlink(leaf,dir_fd=self.directories[parent])
            for name in ('refs','objects/info','objects/pack','objects'):
                parent,_,leaf=name.rpartition('/')
                os.rmdir(leaf,dir_fd=self.directories[parent])
                os.close(self.directories.pop(name))
            self.check_control()
            os.rmdir(self.control)
        for name in ('control_fd','origin_fd','objects_fd','origin_refs_fd','origin_heads_fd','origin_lock_fd','origin_objects_fd','origin_info_fd','origin_pack_fd'):
            fd=getattr(self,name)
            if fd is not None:os.close(fd);setattr(self,name,None)
        self.directories.clear()

    def check_control_inventory(self):
        require(set(self.directories)=={'','refs','objects','objects/info','objects/pack'},
                'incomplete owned Git context; preserved')
        for name,fd in self.directories.items():
            if not name:continue
            parent,_,leaf=name.rpartition('/')
            require(_inode(os.fstat(fd))==_inode(os.stat(leaf,dir_fd=self.directories[parent],follow_symlinks=False)),
                    'owned Git context directory replaced; preserved')
        for name,(inode,digest,length) in self.created.items():
            parent,_,leaf=name.rpartition('/')
            fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.directories[parent])
            try:
                info=os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and _inode(info)==inode
                        and info.st_size==length,'owned Git control file changed; preserved')
                payload=bytearray()
                while len(payload)<=length:
                    part=os.read(fd,min(65536,length+1-len(payload)))
                    if not part:break
                    payload.extend(part)
                require(len(payload)==length and sha256(payload).hexdigest()==digest,
                        'owned Git control bytes changed; preserved')
            finally:os.close(fd)
        expected={'HEAD','config','refs','objects'}|({'shallow'} if 'shallow' in self.created else set())
        require(set(os.listdir(self.control_fd))==expected and not os.listdir(self.directories['refs'])
                and set(os.listdir(self.directories['objects']))=={'info','pack'}
                and not os.listdir(self.directories['objects/pack'])
                and set(os.listdir(self.directories['objects/info']))=={'alternates'},
                'owned Git control inventory changed; preserved')

    def check_control(self):
        require(_inode(os.fstat(self.control_fd))==self.control_identity
                ==_inode(os.stat(self.control,follow_symlinks=False)),'owned Git control replaced; preserved')


# checkout/v4 persists one HTTP token header in .git/config. Only the Git
# authentication child consumes it; no credential is copied to argv, control
# files, parent state, reports or output. This is not host/controller admission.
def _file_stamp(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


class CheckoutHTTPSCarrier:
    """Original process-local checkout header descriptor; never a serialized grant."""
    def __init__(self, repo, destination, *, tls_ca_file=None):
        from urllib.parse import urlsplit
        import re
        parsed=urlsplit(destination)
        require(type(repo) is type(Path()) and repo.is_absolute() and type(destination) is str
                and parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment and '%' not in destination
                and re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git',parsed.path)
                and all(x not in ('.','..') for x in parsed.path.split('/')),
                'finite literal HTTPS repository destination required')
        import threading
        self._use_lock=threading.Lock();self._attempt=None;self._closed=False
        self.pid,self.repo,self.destination=os.getpid(),repo,destination
        self.key='http.'+parsed.scheme+'://'+parsed.netloc+'/.extraheader'
        self.git_dir=self.config_fd=self.ca_fd=None
        self.ca_path=self.ca_stamp=None
        try:
            self.git_dir=_open_directory(repo/'.git')
            self.config_fd=os.open('config',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.git_dir)
            info=os.fstat(self.config_fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and 0<info.st_size<=1048576,
                    'original finite checkout configuration required')
            self.config_stamp=_file_stamp(info)
            if tls_ca_file is not None:
                require(type(tls_ca_file) is type(Path()) and tls_ca_file.is_absolute(),'explicit TLS trust file required')
                self.ca_path=tls_ca_file
                self.ca_fd=os.open(tls_ca_file,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                info=os.fstat(self.ca_fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and 0<info.st_size<=1048576,
                        'finite original TLS trust file required')
                self.ca_stamp=_file_stamp(info)
            self.check()
        except BaseException:
            for fd in (self.ca_fd,self.config_fd,self.git_dir):
                if fd is not None:os.close(fd)
            self._closed=True
            raise

    def check(self):
        require(not self._closed and os.getpid()==self.pid,'original HTTPS authentication carrier closed or transferred')
        require(_inode(os.fstat(self.git_dir))==_inode(os.stat(self.repo/'.git',follow_symlinks=False))
                and _file_stamp(os.fstat(self.config_fd))==self.config_stamp
                ==_file_stamp(os.stat('config',dir_fd=self.git_dir,follow_symlinks=False)),
                'original checkout authentication carrier changed')
        if self.ca_fd is not None:
            require(_file_stamp(os.fstat(self.ca_fd))==self.ca_stamp
                    ==_file_stamp(os.stat(self.ca_path,follow_symlinks=False)), 'original TLS trust carrier changed')

    def close_known(self,attempt):
        require(self._attempt is attempt and not attempt.uncertain,'uncertain authentication carrier retained')
        self.check()
        for fd in (self.config_fd,self.git_dir,self.ca_fd):
            if fd is not None:os.close(fd)
        self._closed=True;self._use_lock.release()

    def __reduce__(self):raise TypeError('HTTPS authentication carrier cannot transfer')


# Reads precisely one checkout header with includes disabled and checks its
# original file incarnation around that read. Subsequent Git uses only the
# consumed value and a literal destination; mutable checkout config is never
# consulted again. Error output is suppressed; no secret leaves this child.
_HTTPS_EXEC = r'''import base64,json,os,signal,stat,subprocess,sys,time
fd=int(sys.argv[1]);stamp=tuple(json.loads(sys.argv[2]));key=sys.argv[3];git=sys.argv[4]
endpoint=int(sys.argv[5]);alarm_endpoint=int(sys.argv[6]);control=int(sys.argv[7]);ca=int(sys.argv[8]);args=sys.argv[9:]
def ident(i):return (i.st_dev,i.st_ino,i.st_mode,i.st_nlink,i.st_size,i.st_mtime_ns,i.st_ctime_ns)
def check():
 if time.monotonic_ns()>=endpoint or ident(os.fstat(fd))!=stamp:raise RuntimeError('original authentication unavailable')
check();os.fchdir(control);os.lseek(fd,0,os.SEEK_SET)
if ca>=0:os.lseek(ca,0,os.SEEK_SET)
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_') and k.upper() not in
 ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','CURL_CA_BUNDLE','SSL_CERT_FILE','SSL_CERT_DIR',
  'NETRC','SSLKEYLOGFILE','CURL_SSL_BACKEND')}
env.update(HOME=os.getcwd(),XDG_CONFIG_HOME=os.getcwd(),GIT_CONFIG_NOSYSTEM='1',
 GIT_CONFIG_SYSTEM=os.devnull,GIT_CONFIG_GLOBAL=os.devnull,GIT_CONFIG_COUNT='0',
 GIT_DIR='.',GIT_COMMON_DIR='.',GIT_TERMINAL_PROMPT='0',GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1')
read=subprocess.Popen([git,'config','--no-includes','--file=/dev/fd/'+str(fd),'--get-all',key],
 stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,pass_fds=(fd,))
# The original configuration is finite. No returned credential is ever logged.
header=read.stdout.read(16385);read.stdout.close()
rc=read.wait(timeout=max(0.001,(endpoint-time.monotonic_ns())/1e9));check()
if rc or len(header)>16384 or not header.endswith(b'\n') or b'\n' in header[:-1] or b'\r' in header:sys.exit(2)
header=header[:-1]
if not header.lower().startswith(b'authorization: basic '):sys.exit(2)
try:decoded=base64.b64decode(header.split(b' ',2)[2],validate=True)
except Exception:sys.exit(2)
if not decoded.startswith(b'x-access-token:') or len(decoded)<=15:sys.exit(2)
settings=[('protocol.allow','never'),('protocol.https.allow','always'),('http.followRedirects','false'),
 ('http.sslVerify','true'),('http.proxy',''),('credential.helper',''),('gc.auto','0'),
 ('maintenance.auto','false'),(key,header.decode('ascii'))]
if ca>=0:settings.append(('http.sslCAInfo','/dev/fd/'+str(ca)))
env['GIT_CONFIG_COUNT']=str(len(settings))
for i,(k,v) in enumerate(settings):env['GIT_CONFIG_KEY_'+str(i)]=k;env['GIT_CONFIG_VALUE_'+str(i)]=v
check()
remaining=(min(endpoint,alarm_endpoint or endpoint)-time.monotonic_ns())//1000000000
if remaining<=0:sys.exit(2)
signal.alarm(remaining)
os.execve(git,[git,'--git-dir=.','--bare',*args],env)
'''


def _require_https_update_ack(data, *, destination, candidate_oid, accepted_tip_oid):
    """Credit only this Git push's one exact fast-forward update response.

    A matching ref is not effect attribution: another writer may have installed
    the identical candidate before our push. Up-to-date/new/forced/partial or
    ambiguous porcelain responses remain unresolved on their original attempt.
    """
    import re
    require(type(data) is bytes and data.endswith(b'\n') and b'\r' not in data,
            'original HTTPS update acknowledgement incomplete')
    lines=data.split(b'\n')
    require(len(lines)==4 and lines[0]==b'To '+destination.encode() and lines[2:]==[b'Done',b''],
            'original HTTPS update acknowledgement missing or ambiguous')
    fields=lines[1].split(b'\t')
    require(len(fields)==3 and fields[0]==b' '
            and fields[1]==(candidate_oid+':refs/heads/main').encode(),
            'original HTTPS exact ref update not acknowledged; matching readback is insufficient')
    endpoints=fields[2].split(b'..')
    require(len(endpoints)==2 and all(re.fullmatch(b'[0-9a-f]{7,40}',part) for part in endpoints)
            and accepted_tip_oid.encode().startswith(endpoints[0])
            and candidate_oid.encode().startswith(endpoints[1]),
            'original HTTPS update does not acknowledge the exact accepted-to-candidate transition')


class _HTTPSPublicationAttempt(_OriginalPublicationAttempt):
    def __init__(self,checked,prepared,*,https_carrier,**original):
        require(type(https_carrier) is CheckoutHTTPSCarrier,'exact original checkout HTTPS carrier required')
        self.carrier=https_carrier;self.carrier.check()
        require(self.carrier._use_lock.acquire(blocking=False),'nested or concurrent authentication carrier refused')
        try:
            require(self.carrier._attempt is None,'original authentication carrier already used')
            super().__init__(checked,prepared,**original)
            require(self.origin_inode is None and self.carrier.repo==self.repo,'network origin is not a local directory inode')
            require(sha256(self.carrier.destination.encode()).hexdigest()==self.origin_digest,'original HTTPS destination differs')
            self.carrier._attempt=self
        except BaseException:
            self.carrier._use_lock.release()
            raise

    def check(self,*,full=False):
        super().check(full=full)
        self.carrier.check()

    def authority(self,method,phase):
        evidence=getattr(self.checked.live.gate,'evidence',None);assertion=getattr(evidence,method,None)
        require(callable(assertion),'actual original HTTPS publication authority unavailable')
        live=self.checked.live
        context=dict(gate=live.gate,repo=self.repo,commit_oid=live.installed,
            operation_id=live.binding.operation_id,lane_id=live.binding.lane_id,budget_id=live.budget,
            retention_id=live.retention,phase=phase,publication_candidate_oid=self.prepared.candidate_oid,
            publication_tree_oid=self.prepared.tree_oid,original_manifest_digest=self.checked.invocation.manifest_digest,
            original_origin_inode=None,origin_binding_sha256=self.origin_digest,original_attempt=self.ordinal,
            original_max_attempts=self.maximum,original_alarm_seconds=self.alarm,git_executable=self.git,
            publication_transport='checkout_https',authentication_config_identity=self.carrier.config_stamp,
            git_pid=self.push_process.pid if self.push_process is not None else None,
            native_checked=self.checked,native_prepared=self.prepared,native_attempt=self)
        from scripts.ci.qledger_owner_invocation import publication_assertion_scope
        with publication_assertion_scope(self, method):
            require(assertion(**context) is None,'authority returned an admission flag')
        self.check()  # Caught evidence failure cannot rehabilitate this original.

    def setup(self):
        self.check(full=True)
        require(self.origin_bytes()==self.carrier.destination.encode(),'original HTTPS origin changed')
        self.authority('assert_resources','native-https-intent');self.authority('assert_process_version','native-https-intent')
        root=self.checked.invocation._original().owner_root
        self.control=Path(tempfile.mkdtemp(prefix='.qledger-git-control-',dir=root))
        self.control_fd=_open_directory(self.control);self.control_identity=_inode(os.fstat(self.control_fd))
        self.directories['']=self.control_fd
        for name in ('refs','objects','objects/info','objects/pack'):
            parent,_,leaf=name.rpartition('/');os.mkdir(leaf,mode=0o700,dir_fd=self.directories[parent])
            self.directories[name]=os.open(leaf,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.directories[parent])
        raw,_=candidate.publication._git(self.repo,['rev-parse','--git-path','objects'],output_limit=4096)
        objects=Path(os.fsdecode(raw.rstrip(b'\n')))
        if not objects.is_absolute():objects=self.repo/objects
        self.objects_fd=_open_directory(objects);self.objects_path=objects
        self._file('HEAD',b'ref: refs/heads/unused\n');self._file('config',b'[core]\n bare = true\n repositoryformatversion = 0\n')
        self._file('objects/info/alternates',(str(objects)+'\n').encode())
        raw,_=candidate.publication._git(self.repo,['rev-parse','--git-path','shallow'],output_limit=4096)
        shallow=Path(os.fsdecode(raw.rstrip(b'\n')))
        if not shallow.is_absolute():shallow=self.repo/shallow
        if shallow.exists():
            fd=os.open(shallow,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:payload=os.read(fd,1048577)
            finally:os.close(fd)
            require(len(payload)<=1048576 and all(len(x)==40 and all(c in b'0123456789abcdef' for c in x) for x in payload.splitlines()),'unqualified shallow metadata')
            self._file('shallow',payload)
        self.check()

    def run_git(self,args,*,effect=False):
        import json
        self.check(full=effect)
        if effect:
            require(not self.effect_started,'original HTTPS attempt already entered; no replay')
            self.alarm_started_ns=time.monotonic_ns();self.uncertain=True;self.effect_started=True
            command=['push','--porcelain','--force-with-lease=refs/heads/main:'+self.prepared.accepted_tip_oid,
                     '--',self.carrier.destination,self.prepared.candidate_oid+':refs/heads/main']
        else:
            command=['ls-remote','--refs','--exit-code','--',self.carrier.destination,'refs/heads/main']
        alarm_endpoint=0
        if self.alarm_started_ns is not None and self.alarm:
            alarm_endpoint=self.alarm_started_ns+self.alarm*1_000_000_000
            require(time.monotonic_ns()<alarm_endpoint,'unchanged original HTTPS attempt alarm exhausted')
        fds=[self.carrier.config_fd,self.control_fd,self.objects_fd]
        if self.carrier.ca_fd is not None:fds.append(self.carrier.ca_fd)
        child=subprocess.Popen([sys.executable,'-I','-c',_HTTPS_EXEC,str(self.carrier.config_fd),
            json.dumps(self.carrier.config_stamp),self.carrier.key,self.git,
            str(self.checked.original_deadline),str(alarm_endpoint),str(self.control_fd),
            str(self.carrier.ca_fd if self.carrier.ca_fd is not None else -1),*command],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,pass_fds=tuple(fds))
        self.process=child
        if effect:self.push_process=child
        self.uncertain=True
        data=self.wait_network(child)
        self.last_response=(data,b'',child.returncode)
        if effect:self.push_response=self.last_response
        require(child.returncode==0,'original authenticated Git completion unproven; no retry or guessed cleanup')
        if effect:_require_https_update_ack(data,destination=self.carrier.destination,
            candidate_oid=self.prepared.candidate_oid,accepted_tip_oid=self.prepared.accepted_tip_oid)
        self.check()
        self.uncertain=self.effect_started and not self.remote_confirmed
        return data

    def wait_network(self,child):
        data=bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout,selectors.EVENT_READ)
            while selector.get_map():
                self.check();ready=selector.select(min(self.checked._deadline(),0.25));self.check()
                for key,_ in ready:
                    part=os.read(key.fd,min(65536,16385-len(data)))
                    if not part:selector.unregister(key.fileobj)
                    data.extend(part);require(len(data)<=16384,'HTTPS protocol output exceeds original bound; process retained')
            child.wait(timeout=self.checked._deadline())
        child.stdout.close();return bytes(data)

    def readback(self,oid):
        raw=self.run_git(['rev-parse','--verify','refs/heads/main'])
        require(raw==(oid+'\trefs/heads/main\n').encode(),'exact authenticated original-origin full candidate not confirmed')
        self.check()

    def close_known(self):
        if self.uncertain:return
        super().close_known()
        self.carrier.close_known(self)

    def perform(self,reader):
        self.setup();self.readback(self.prepared.accepted_tip_oid)
        self.run_git([],effect=True);self.readback(self.prepared.candidate_oid)
        self.origin_bytes();self.check(full=True)
        self.authority('assert_publication_readback','native-https-readback')
        self.authority('assert_descendants_settled','native-https-readback')
        self.remote_confirmed=True;self.uncertain=False
        generation=NativePublishedGeneration(self,_SEAL)
        if reader is not None:generation.reader_result=generation.invoke_reader(reader)
        self.check();self.confirmed=True;return generation


def publish(checked,prepared,*,reader=None,**original):
    from scripts.ci.qledger_engine_publication import _LiveFinalCandidate
    require(type(checked) is _LiveFinalCandidate,'actual live finalizer required')
    require(checked.publication_guard.acquire(blocking=False),'nested or concurrent publication refused')
    try:
        checked._check()
        require(checked.publication_attempt is None,'original publication already entered; no replay')
        factory=_HTTPSPublicationAttempt if 'https_carrier' in original else _OriginalPublicationAttempt
        attempt=factory(checked,prepared,**original)
        checked.publication_attempt=attempt
        return attempt.perform(reader)
    except BaseException as exc:
        checked.failure=checked.failure or exc
        raise
    finally:checked.publication_guard.release()


def confirmed(checked):
    value=checked.publication_attempt
    if value is None:return False
    require(type(value) in (_OriginalPublicationAttempt,_HTTPSPublicationAttempt) and value._seal is _SEAL and value.checked is checked,
            'original publication state cannot be substituted')
    return value.confirmed and not value.uncertain


class NativePublicationFinalizer:
    """Opt-in actual daily prepare/update/readback; no authority is issued here."""
    def __init__(self, *, reader=None, origin_binding_sha256, original_origin_inode,
                 original_attempt, original_max_attempts, original_alarm_seconds, https_carrier=None):
        self.pid = os.getpid()
        self.reader = reader
        self.original = dict(origin_binding_sha256=origin_binding_sha256,
            original_origin_inode=original_origin_inode, original_attempt=original_attempt,
            original_max_attempts=original_max_attempts, original_alarm_seconds=original_alarm_seconds)
        if https_carrier is not None:self.original['https_carrier']=https_carrier
        self.generation = None

    def __call__(self, checked):
        require(os.getpid() == self.pid, 'original publication finalizer transferred')
        from scripts.ci.qledger_engine_publication import finalize_daily_engine_outputs
        prepared = finalize_daily_engine_outputs(checked)
        self.generation = publish(checked, prepared, reader=self.reader, **self.original)
        gate=checked.live.gate
        if getattr(gate,'_native_transition',False):
            from scripts.ci.qledger_host_gate import HostGate
            require(type(gate) is HostGate,'actual native generation controller required')
            gate.confirm_native_generation(checked,self.generation)
        return prepared

    def __reduce__(self):
        raise TypeError('original publication finalizer cannot transfer')
