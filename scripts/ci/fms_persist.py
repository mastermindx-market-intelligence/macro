"""Persist an already-acquired FMS commit without rerunning acquisition.

Only an authenticated definite contention rejection may be retried. A lost reply
gets one same-origin observation; absent confirmation remains effect-unknown.
This module does not acquire sources, rebuild projections or publish site data.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, subprocess, tempfile, time
from pathlib import Path

FMS_FILES = tuple('data/government_revenue/fms_' + n for n in (
    'collection_receipts.jsonl', 'observations.jsonl', 'projection_state.json', 'case_graph.json'))
# A projection may only be transplanted over changes outside its source closure.
SOURCE_PREFIXES = ('.github/workflows/', 'collectors/', 'engine/government_revenue/',
                   'config/government_revenue/', 'contracts/', 'engine/__init__.py',
                   'engine/research_vault/', 'data/government_revenue/fms_staged_objects/',
                   'scripts/', 'lib/', 'requirements', 'pyproject.toml')
UNKNOWN = 75
REFUSED = 76

class Refusal(ValueError):
    pass

def git(root, *args, env=None, timeout=30):
    return subprocess.run(['git', '-C', str(root), *args], env={**os.environ, **(env or {}), 'GIT_OPTIONAL_LOCKS':'0',
                          'GIT_NO_REPLACE_OBJECTS':'1', 'GIT_NO_LAZY_FETCH':'1'},
                          capture_output=True, timeout=timeout)

def need(root, *args, env=None,reader=None):
    r=reader(root,*args) if reader is not None else git(root,*args,env=env)
    if r.returncode: raise Refusal('git_read_or_local_preparation_failed')
    return r.stdout

def save(path, value, *, create=False):
    with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
        f.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno());name=f.name
    try:
        if create:os.link(name,path)  # Atomic admission; never overwrite another original operation.
        else:os.replace(name,path)
    except FileExistsError as exc:
        raise Refusal('receipt_identity_already_exists') from exc
    finally:
        if os.path.exists(name):os.unlink(name)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def origin(root):
    fetch=need(root,'remote','get-url','--all','origin').splitlines()
    push=need(root,'remote','get-url','--push','--all','origin').splitlines()
    if len(fetch)!=1 or fetch!=push:raise Refusal('origin_binding_changed_or_ambiguous')
    return hashlib.sha256(fetch[0]).hexdigest()

def remote_head(root,ref,binding):
    if origin(root)!=binding:raise Refusal('origin_binding_changed')
    rows=need(root,'ls-remote','--refs','origin',ref).decode().splitlines()
    if len(rows)!=1:raise Refusal('selected_remote_branch_missing_or_ambiguous')
    sha,name=rows[0].split()
    if name!=ref or not re.fullmatch('[0-9a-f]{40}',sha):raise Refusal('remote_branch_identity_invalid')
    need(root,'fetch','--no-tags','--no-write-fetch-head','origin',ref)
    # The named object must now exist; a concurrent move may leave it absent.
    need(root,'cat-file','-e',sha+'^{commit}')
    return sha

def ancestor(root,older,newer,*,reader=None):
    return (reader or git)(root,'merge-base','--is-ancestor',older,newer).returncode==0

def changed_paths(root,older,newer,*,reader=None):
    # NUL-delimited paths bypass Git C-quoting; no-renames exposes both the
    # source deletion and destination addition, including moves out of closure.
    return tuple(os.fsdecode(p) for p in need(root,'diff','--name-only','-z',
                 '--no-renames',older,newer,reader=reader).split(b'\0') if p)

def artifact_entry(root,candidate,name,*,reader=None):
    entry=need(root,'ls-tree',candidate,'--',name,reader=reader).decode().strip().split()
    if len(entry)!=4:raise Refusal('fms_artifact_missing_in_acquisition')
    mode,kind,oid,path=entry
    if mode!='100644' or kind!='blob' or path!=name:raise Refusal('fms_artifact_not_regular_file')
    return mode,oid

def validate_acquisition_commit(root, candidate,*,reader=None):
    """Read-only original acquisition contract, also usable by trusted fences.

    The caller authenticates the producer and original source head. This
    function neither infers producer identity nor admits/queues a candidate.
    """
    if not isinstance(candidate,str) or not re.fullmatch('[0-9a-f]{40}',candidate):
        raise Refusal('immutable_acquisition_commit_required')
    line=need(root,'rev-list','--parents','-n','1',candidate,reader=reader).decode().split()
    if len(line)!=2:raise Refusal('one_acquisition_parent_required')
    candidate,base=line
    changed=set(changed_paths(root,base,candidate,reader=reader))
    if not changed or not changed<=set(FMS_FILES):raise Refusal('acquisition_commit_outside_four_files')
    for name in FMS_FILES:artifact_entry(root,candidate,name,reader=reader)
    for name in FMS_FILES[:2]:
        prior=need(root,'show',base+':'+name,reader=reader);current=need(root,'show',candidate+':'+name,reader=reader)
        if not current.startswith(prior):raise Refusal('append_only_fms_source_changed')
    return candidate,base

def validate_source_movement(root,base,remote,*,reader=None):
    if not ancestor(root,base,remote,reader=reader):raise Refusal('selected_branch_no_longer_descends_from_acquisition_base')
    changed=changed_paths(root,base,remote,reader=reader)
    if any(p in FMS_FILES or p.startswith(SOURCE_PREFIXES) for p in changed):raise Refusal('concurrent_fms_or_source_change_requires_reconciliation')

def validate_native_group(root,candidate,group_base,group_commit,*,git_read=None,deadline=None):
    """Conserve one original acquisition in an authenticated native group.

    Core must bind candidate/group/base to its ORIGINAL NativeAdmission and
    provider group proof before using this result. It must call this fence
    before merge, not infer safety from the later publisher witness. No network,
    mutable checkout/index, receipt, acquisition or publication effects occur.

    Optional git_read(root,*args,timeout=remaining) returns CompletedProcess
    with BYTE stdout. Core charges EACH call to its SAME original read budget
    and supplies its absolute MONOTONIC deadline. No allowance, materialization,
    fetch, implicit lazy fetch or replacement-object admission is created here.
    The default retains the existing local-Git API for original callers.
    """
    for identity in (group_base,group_commit):
        if not isinstance(identity,str) or not re.fullmatch('[0-9a-f]{40}',identity):
            raise Refusal('immutable_native_group_identity_required')
    if git_read is not None and deadline is None:raise Refusal('original_group_deadline_required')
    if deadline is not None and (type(deadline) not in (int,float) or not math.isfinite(deadline)):
        raise Refusal('original_group_deadline_invalid')
    def bounded_read(where,*args):
        if not args or args[0] not in ('rev-list','merge-base','diff','ls-tree','show'):
            raise Refusal('native_group_read_only_scope_required')
        remaining=30 if deadline is None else min(30,deadline-time.monotonic())
        if remaining<=0:raise Refusal('original_group_deadline_expired')
        result=(git_read or git)(where,*args,timeout=remaining)
        if deadline is not None and time.monotonic()>=deadline:raise Refusal('original_group_deadline_expired')
        if type(result.returncode) is not int or not isinstance(result.stdout,bytes):
            raise Refusal('native_group_git_read_result_unqualified')
        return result
    candidate,base=validate_acquisition_commit(root,candidate,reader=bounded_read)
    validate_source_movement(root,base,group_base,reader=bounded_read)
    projection={name:artifact_entry(root,candidate,name,reader=bounded_read) for name in FMS_FILES}
    if any(artifact_entry(root,group_commit,name,reader=bounded_read)!=entry for name,entry in projection.items()):
        raise Refusal('native_group_changed_original_fms_projection')
    # Changes introduced by integration outside the four sealed files must be
    # unrelated too; an unauthenticated caller cannot substitute a group tree
    # containing a source change while presenting a clean group_base.
    changed=changed_paths(root,group_base,group_commit,reader=bounded_read)
    if any(p not in FMS_FILES and p.startswith(SOURCE_PREFIXES) for p in changed):
        raise Refusal('native_group_changed_original_fms_source')
    return {'candidate':candidate,'acquisition_base':base,'group_base':group_base,
            'group_commit':group_commit,'projection_sha256':hashlib.sha256(
                json.dumps(projection,sort_keys=True,separators=(',',':')).encode()).hexdigest()}

def validate_acquisition(root):
    if need(root,'status','--porcelain','--untracked-files=all').strip():raise Refusal('acquisition_commit_not_clean')
    return validate_acquisition_commit(root,need(root,'rev-parse','HEAD').decode().strip())

def prepare(root,base,candidate,remote,out):
    validate_source_movement(root,base,remote)
    if remote==base:return candidate
    # An isolated temporary index preserves the actual checkout/index and writers.
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='fms-index-') as temp:
        env={**os.environ,'GIT_INDEX_FILE':str(Path(temp)/'index')}
        need(root,'read-tree',remote,env=env)
        for name in FMS_FILES:
            mode,oid=artifact_entry(root,candidate,name)
            need(root,'update-index','--add','--cacheinfo',mode,oid,name,env=env)
        tree=need(root,'write-tree',env=env).decode().strip()
        message=need(root,'show','-s','--format=%B',candidate).decode().strip()
        author=need(root,'show','-s','--format=%an%x00%ae%x00%aI',candidate).decode().rstrip('\n').split('\0')
        env.update(zip(('GIT_AUTHOR_NAME','GIT_AUTHOR_EMAIL','GIT_AUTHOR_DATE'),author))
        return need(root,'commit-tree',tree,'-p',remote,'-m',message,env=env).decode().strip()

def classify(result):
    body=result.stdout+result.stderr
    if result.returncode==0:return 'acknowledged'
    if re.search(rb'error: GH00[16]:|error: GH013:|permission denied|permission to .* denied',body,re.I):return 'refused'
    lines=[x for x in result.stdout.splitlines() if x.startswith((b'!\t',b' \t',b'*\t',b'+\t',b'=\t',b'-\t'))]
    if result.returncode==1 and len(lines)==1 and re.fullmatch(rb'!\t[^\t]+\t\[rejected\] \((?:fetch first|non-fast-forward|stale info)\)',lines[0]):return 'definite_contention_rejection'
    return 'effect_unknown'

def persist(root,branch,out,max_attempts=3,*,native_deadline=0):
    root=Path(root).resolve();out=Path(out).resolve()
    if native_deadline and (type(native_deadline) not in (int,float)
            or not math.isfinite(native_deadline) or not 0<native_deadline-time.time()<=135):
        raise Refusal('original_fms_publication_budget_invalid')
    if out.is_relative_to(root) or out.exists() or not 1<=max_attempts<=3:raise Refusal('receipt_identity_or_attempt_bound_invalid')
    if git(root,'check-ref-format','refs/heads/'+branch).returncode:raise Refusal('invalid_target_branch')
    out.parent.mkdir(parents=True,exist_ok=True)
    candidate,base=validate_acquisition(root);binding=origin(root);ref='refs/heads/'+branch
    rec={'contract':'fms.acquisition_persistence.v1','candidate':candidate,'base':base,'target_ref':ref,'origin_sha256':binding,'attempts':[],'state':'PREPARED_NO_PUSH'}
    save(out,rec,create=True)
    try:
        if native_deadline:
            from scripts.ci import native_queue_push as native
            try:
                status,record=native.prepare_publication(root,['origin',candidate+':'+ref],native_deadline)
            except native.EffectUnknown:
                rec['state']='EFFECT_UNKNOWN';save(out,rec);return UNKNOWN
            except (native.PublicationHeld,OSError,ValueError,subprocess.SubprocessError):
                rec['state']='NATIVE_PUBLICATION_HELD';save(out,rec);return REFUSED
            if status==native.PENDING:
                rec.update(state='NATIVE_PUBLICATION_PENDING',native_origin_path=str(record),
                           native_deadline=native_deadline)
                rec['attempts'].append({'expected_commit':candidate,'state':'native_pending'})
                save(out,rec)
                with open(os.environ['GITHUB_OUTPUT'],'a') as output:
                    output.write('native_deadline='+str(native_deadline)+'\n')
                return native.PENDING
            if status!=native.LEGACY:
                rec['state']='NATIVE_PUBLICATION_HELD';save(out,rec);return REFUSED
        for _ in range(max_attempts):
            remote=remote_head(root,ref,binding)
            expected=prepare(root,base,candidate,remote,out)
            if need(root,'rev-parse','HEAD').decode().strip()!=candidate or need(root,'status','--porcelain').strip():raise Refusal('local_acquisition_changed')
            attempt={'expected_commit':expected,'observed_predecessor':remote,'state':'PUSH_ATTEMPT_STARTED'};rec['attempts'].append(attempt);rec['state']='EFFECT_UNKNOWN';save(out,rec)
            try:
                result=git(root,'push','--porcelain','origin',expected+':'+ref,timeout=45)
                verdict=classify(result);attempt['response_sha256']=hashlib.sha256(result.stdout+result.stderr).hexdigest()
            except subprocess.TimeoutExpired:verdict='effect_unknown'
            attempt['state']=verdict;save(out,rec)
            if verdict=='refused':rec['state']='REFUSED';save(out,rec);return REFUSED
            if verdict=='definite_contention_rejection':continue
            # A success response is checked too; no retry follows uncertain output.
            try:
                observed=remote_head(root,ref,binding)
                if ancestor(root,expected,observed):
                    attempt['observed_commit']=observed;rec['state']='ORIGINAL_EFFECT_CONFIRMED';save(out,rec);return 0
            except (Refusal,subprocess.SubprocessError):pass
            rec['state']='EFFECT_UNKNOWN';save(out,rec);return UNKNOWN
        rec['state']='DEFINITE_CONTENTION_BUDGET_EXHAUSTED';save(out,rec);return 1
    except (Refusal,subprocess.SubprocessError) as exc:
        # A failed preparation after a definite rejection has no new push effect.
        live=rec['attempts'] and rec['attempts'][-1]['state'] in ('PUSH_ATTEMPT_STARTED','effect_unknown','acknowledged')
        rec['state']='EFFECT_UNKNOWN' if live else 'PREPARATION_REFUSED_NO_NEW_PUSH'
        rec['reason']=str(exc) if isinstance(exc,Refusal) else 'bounded_git_operation_failed';save(out,rec);return UNKNOWN if live else 1


def settle_native(root,out):
    """Read the SAME original intent, then conserve the FMS domain receipt.

    A pending origin upload never confirms acquisition persistence. No source
    acquisition, intent write, label request or second push is performed here.
    The original receipt stays pending/UNKNOWN on any unconfirmed observation.
    """
    from scripts.ci import native_queue_push as native
    root=Path(root).resolve();out=Path(out).resolve()
    if out.is_relative_to(root) or out.is_symlink():raise Refusal('original_fms_receipt_required')
    rec=json.loads(out.read_text())
    if (rec.get('contract')!='fms.acquisition_persistence.v1'
            or rec.get('state')!='NATIVE_PUBLICATION_PENDING'
            or rec.get('target_ref')!='refs/heads/main'
            or rec.get('attempts')!=[{'expected_commit':rec.get('candidate'),'state':'native_pending'}]):
        raise Refusal('original_pending_fms_receipt_required')
    candidate,base=validate_acquisition(root)
    if candidate!=rec.get('candidate') or base!=rec.get('base') or origin(root)!=rec.get('origin_sha256'):
        raise Refusal('original_acquisition_identity_changed')
    deadline=rec['native_deadline']
    if type(deadline) not in (float,int) or deadline<=0:raise Refusal('original_fms_deadline_required')
    def confirmed(receipt):
        if time.time()>=deadline:raise Refusal('original_fms_publication_budget_expired')
        if receipt.get('source_head')!=candidate:raise Refusal('original_fms_source_head_changed')
        observed=remote_head(root,rec['target_ref'],rec['origin_sha256'])
        merge=receipt['merge_sha']
        if not ancestor(root,merge,observed):raise Refusal('protected_fms_merge_not_observed')
        line=need(root,'rev-list','--parents','-n','1',merge).decode().split()
        if len(line)!=2:raise Refusal('protected_fms_squash_parent_required')
        validate_native_group(root,candidate,line[1],merge,
            deadline=time.monotonic()+max(0,deadline-time.time()))
        if any(artifact_entry(root,candidate,name)!=artifact_entry(root,observed,name) for name in FMS_FILES):
            raise Refusal('protected_fms_generation_superseded')
        if origin(root)!=rec['origin_sha256']:raise Refusal('origin_binding_changed')
        if time.time()>=deadline:raise Refusal('original_fms_publication_budget_expired')
        rec['attempts'][-1].update(state='native_published',observed_commit=observed)
        rec.update(state='ORIGINAL_EFFECT_CONFIRMED',native_publication=receipt)
        save(out,rec)
    try:
        return native.settle(native.GitHub(root,deadline),root,rec['native_origin_path'],deadline,
                             on_published=confirmed)
    except native.EffectUnknown:return UNKNOWN
    except (native.PublicationHeld,Refusal,OSError,ValueError,subprocess.SubprocessError):return REFUSED

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--branch');p.add_argument('--receipt',required=True,type=Path);p.add_argument('--native-deadline',type=float,default=0);p.add_argument('--settle-native',action='store_true');a=p.parse_args()
    if not a.settle_native and not a.branch:p.error('--branch required for original persistence')
    try:raise SystemExit(settle_native(a.root,a.receipt) if a.settle_native else persist(a.root,a.branch,a.receipt,native_deadline=a.native_deadline))
    except Refusal as e:print('fms-persist refused:',str(e));raise SystemExit(1)
