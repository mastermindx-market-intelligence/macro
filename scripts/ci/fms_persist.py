"""Persist an already-acquired FMS commit without rerunning acquisition.

Only an authenticated definite contention rejection may be retried. A lost reply
gets one same-origin observation; absent confirmation remains effect-unknown.
This module does not acquire sources, rebuild projections or publish site data.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, tempfile
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
    return subprocess.run(['git', '-C', str(root), *args], env={**os.environ, **(env or {}), 'GIT_OPTIONAL_LOCKS':'0'},
                          capture_output=True, timeout=timeout)

def need(root, *args, env=None):
    r=git(root,*args,env=env)
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

def ancestor(root,older,newer):
    return git(root,'merge-base','--is-ancestor',older,newer).returncode==0

def changed_paths(root,older,newer):
    # NUL-delimited paths bypass Git C-quoting; no-renames exposes both the
    # source deletion and destination addition, including moves out of closure.
    return tuple(os.fsdecode(p) for p in need(root,'diff','--name-only','-z',
                 '--no-renames',older,newer).split(b'\0') if p)

def artifact_entry(root,candidate,name):
    entry=need(root,'ls-tree',candidate,'--',name).decode().strip().split()
    if len(entry)!=4:raise Refusal('fms_artifact_missing_in_acquisition')
    mode,kind,oid,path=entry
    if mode!='100644' or kind!='blob' or path!=name:raise Refusal('fms_artifact_not_regular_file')
    return mode,oid

def validate_acquisition(root):
    if need(root,'status','--porcelain','--untracked-files=all').strip():raise Refusal('acquisition_commit_not_clean')
    line=need(root,'rev-list','--parents','-n','1','HEAD').decode().split()
    if len(line)!=2:raise Refusal('one_acquisition_parent_required')
    candidate,base=line
    changed=set(changed_paths(root,base,candidate))
    if not changed or not changed<=set(FMS_FILES):raise Refusal('acquisition_commit_outside_four_files')
    for name in FMS_FILES:artifact_entry(root,candidate,name)
    for name in FMS_FILES[:2]:
        prior=need(root,'show',base+':'+name);current=need(root,'show',candidate+':'+name)
        if not current.startswith(prior):raise Refusal('append_only_fms_source_changed')
    return candidate,base

def prepare(root,base,candidate,remote,out):
    if not ancestor(root,base,remote):raise Refusal('selected_branch_no_longer_descends_from_acquisition_base')
    changed=changed_paths(root,base,remote)
    if any(p in FMS_FILES or p.startswith(SOURCE_PREFIXES) for p in changed):raise Refusal('concurrent_fms_or_source_change_requires_reconciliation')
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

def persist(root,branch,out,max_attempts=3):
    root=Path(root).resolve();out=Path(out).resolve()
    if out.is_relative_to(root) or out.exists() or not 1<=max_attempts<=3:raise Refusal('receipt_identity_or_attempt_bound_invalid')
    if git(root,'check-ref-format','refs/heads/'+branch).returncode:raise Refusal('invalid_target_branch')
    out.parent.mkdir(parents=True,exist_ok=True)
    candidate,base=validate_acquisition(root);binding=origin(root);ref='refs/heads/'+branch
    rec={'contract':'fms.acquisition_persistence.v1','candidate':candidate,'base':base,'target_ref':ref,'origin_sha256':binding,'attempts':[],'state':'PREPARED_NO_PUSH'}
    save(out,rec,create=True)
    try:
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

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--branch',required=True);p.add_argument('--receipt',required=True,type=Path);a=p.parse_args()
    try:raise SystemExit(persist(a.root,a.branch,a.receipt))
    except Refusal as e:print('fms-persist refused:',str(e));raise SystemExit(1)
