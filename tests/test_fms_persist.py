from pathlib import Path
import subprocess,json
import pytest
from scripts.ci import fms_persist as m

def run(path,*args):
 r=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True)
 assert r.returncode==0,r.stderr
 return r.stdout.strip()

@pytest.fixture
def fixture(tmp_path):
 origin=tmp_path/'origin.git';root=tmp_path/'acquirer';peer=tmp_path/'peer'
 run(tmp_path,'init','--bare',str(origin));run(tmp_path,'clone',str(origin),str(root));run(root,'checkout','-b','main');run(root,'config','user.name','test');run(root,'config','user.email','test@example.invalid')
 for n in m.FMS_FILES:
  p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}\n')
 helper=root/'scripts/ci/fms_persist.py';helper.parent.mkdir(parents=True);helper.write_bytes(Path(m.__file__).read_bytes())
 (helper.parent/'govrev_source_binding.py').write_bytes(Path(m.__file__).with_name('govrev_source_binding.py').read_bytes())
 (root/'unrelated.txt').write_text('baseline\n');run(root,'add','.');run(root,'commit','-m','baseline');run(root,'push','origin','HEAD:main');run(tmp_path,'clone','--branch','main',str(origin),str(peer));run(peer,'config','user.name','test');run(peer,'config','user.email','test@example.invalid')
 p=root/m.FMS_FILES[1];p.write_text(p.read_text()+'{"new":true}\n');run(root,'add',m.FMS_FILES[1]);run(root,'commit','-m','acquired once')
 return root,origin,peer,tmp_path/'receipt.json'

def advance(peer,path='unrelated.txt',body='new unrelated\n'):
 p=peer/path;p.write_text(body);run(peer,'add',path);run(peer,'commit','-m','concurrent');run(peer,'push','origin','HEAD:main')

def test_transplant_preserves_unrelated_change_and_exact_acquisition(fixture):
 root,origin,peer,out=fixture;head=run(root,'rev-parse','HEAD');advance(peer)
 assert m.persist(root,'main',out)==0
 tip=run(origin,'rev-parse','main');assert run(origin,'show',tip+':unrelated.txt')=='new unrelated'
 assert run(origin,'show',tip+':'+m.FMS_FILES[1])==run(root,'show',head+':'+m.FMS_FILES[1])
 assert run(root,'rev-parse','HEAD')==head and run(root,'status','--porcelain')==''
 assert json.loads(out.read_text())['state']=='ORIGINAL_EFFECT_CONFIRMED'
 with pytest.raises(m.Refusal,match='receipt_identity'):m.persist(root,'main',out)

@pytest.mark.parametrize('path',[m.FMS_FILES[1],'scripts/guard.py','engine/research_vault/r2_store.py','data/government_revenue/fms_staged_objects/manifest.json'])
def test_source_or_fms_overlap_refuses_before_push(fixture,path):
 root,origin,peer,out=fixture;(peer/Path(path).parent).mkdir(parents=True,exist_ok=True);advance(peer,path,'changed\n');before=run(origin,'rev-parse','main')
 assert m.persist(root,'main',out)==1
 assert run(origin,'rev-parse','main')==before and json.loads(out.read_text())['attempts']==[]

@pytest.mark.parametrize('kind',['contention','lost_reply','unknown','permission'])
def test_real_git_races_and_uncertain_reply_keep_original_effect(fixture,monkeypatch,kind):
 root,origin,peer,out=fixture;real=m.git;pushes=[]
 def wrapped(where,*args,**kw):
  if args and args[0]=='push':
   pushes.append(args)
   if len(pushes)==1:
    if kind=='contention':advance(peer)
    elif kind=='lost_reply':
     r=real(where,*args,**kw);assert r.returncode==0
     return subprocess.CompletedProcess(args,128,b'',b'transport lost after send')
    elif kind=='unknown':return subprocess.CompletedProcess(args,128,b'',b'transport lost')
    elif kind=='permission':return subprocess.CompletedProcess(args,1,b'',b'error: GH013: repository rule violation')
  return real(where,*args,**kw)
 monkeypatch.setattr(m,'git',wrapped);rc=m.persist(root,'main',out);r=json.loads(out.read_text())
 expected={'contention':(0,2,'ORIGINAL_EFFECT_CONFIRMED'),'lost_reply':(0,1,'ORIGINAL_EFFECT_CONFIRMED'),'unknown':(75,1,'EFFECT_UNKNOWN'),'permission':(76,1,'REFUSED')}[kind]
 assert (rc,len(pushes),r['state'])==expected
 if kind=='contention':assert r['attempts'][0]['state']=='definite_contention_rejection'


def test_append_only_prefix_is_required(fixture):
 root,origin,peer,out=fixture;(root/m.FMS_FILES[1]).write_text('replacement\n');run(root,'add',m.FMS_FILES[1]);run(root,'commit','--amend','--no-edit')
 with pytest.raises(m.Refusal,match='append_only'):m.persist(root,'main',out)
 assert not out.exists()


def test_definite_contention_is_bounded_and_no_acquisition_is_replayed(fixture,monkeypatch):
 root,origin,peer,out=fixture;real=m.git;pushes=[]
 def racing(where,*args,**kw):
  if args and args[0]=='push':
   pushes.append(args);advance(peer,body='concurrent '+str(len(pushes))+'\n')
  return real(where,*args,**kw)
 monkeypatch.setattr(m,'git',racing)
 assert m.persist(root,'main',out)==1
 r=json.loads(out.read_text());assert len(pushes)==3 and r['state']=='DEFINITE_CONTENTION_BUDGET_EXHAUSTED'
 assert run(origin,'show','main:'+m.FMS_FILES[1])=='{}'


def test_proposed_workflow_persist_shell_preserves_concurrent_source(fixture):
 import os,sys,yaml
 root,origin,peer,out=fixture
 run(root,'push','origin','HEAD:main');run(peer,'pull','--ff-only','origin','main')
 p=root/m.FMS_FILES[1];p.write_text(p.read_text()+'{"next":true}\n')
 advance(peer,body='next unrelated\n')
 y=yaml.load((Path(__file__).resolve().parents[1]/'.github/workflows/fms-acquire.yml').read_text(),Loader=yaml.BaseLoader)
 step=next(x for x in y['jobs']['acquire']['steps'] if x.get('id')=='persist')
 env={**os.environ,'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'],'FMS_TARGET_REF':'main','FMS_DEFAULT_BRANCH':'main','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ID':'local-fixture','GITHUB_RUN_ATTEMPT':'1','RUNNER_TEMP':str(out.parent),'GITHUB_OUTPUT':str(out.parent/'outputs')}
 env.pop('PYTHONPATH',None)
 r=subprocess.run(['bash','-e','-o','pipefail','-c',step['run']],cwd=root,env=env,capture_output=True,text=True)
 assert r.returncode==0,r.stdout+r.stderr
 outputs=dict(line.split('=',1) for line in (out.parent/'outputs').read_text().splitlines())
 assert outputs['publish_default']=='true'
 confirmed=run(origin,'rev-parse','main')
 assert outputs['source_sha']==confirmed
 assert confirmed!=run(root,'rev-parse','HEAD'), 'the settled transplant, not original acquisition HEAD, must be handed off'
 assert run(origin,'show','main:'+m.FMS_FILES[1]).endswith('{"next":true}')
 assert run(origin,'show','main:unrelated.txt')=='next unrelated'
 assert json.loads((out.parent/'fms-persist-local-fixture-1.json').read_text())['state']=='ORIGINAL_EFFECT_CONFIRMED'


def test_same_receipt_race_cannot_overwrite_confirmed_original_effect(fixture,monkeypatch):
 root,origin,peer,out=fixture;real=m.origin;entered=False;completed={}
 def race(where):
  nonlocal entered
  if not entered:
   entered=True
   # The outer invocation passed exists(); a second invocation finishes before
   # the outer can create its initial receipt. Use the actual Git push/readback.
   assert m.persist(root,'main',out)==0
   completed['bytes']=out.read_bytes()
  return real(where)
 monkeypatch.setattr(m,'origin',race)
 with pytest.raises(m.Refusal,match='receipt_identity'):
  m.persist(root,'main',out)
 assert out.read_bytes()==completed['bytes']
 assert json.loads(out.read_text())['state']=='ORIGINAL_EFFECT_CONFIRMED'


@pytest.mark.parametrize('kind',['rename_out','quoted_source','newline_source'])
def test_source_closure_handles_git_path_encoding_and_renames(fixture,kind):
 root,origin,peer,out=fixture
 if kind=='rename_out':
  (peer/'docs').mkdir();run(peer,'mv','scripts/ci/fms_persist.py','docs/moved_helper.py');run(peer,'commit','-m','move source');run(peer,'push','origin','HEAD:main')
 else:
  name='config/government_revenue/'+('révenue.yaml' if kind=='quoted_source' else 'other\nsource.yaml')
  (peer/Path(name).parent).mkdir(parents=True,exist_ok=True);advance(peer,name,'changed source\n')
 before=run(origin,'rev-parse','main')
 assert m.persist(root,'main',out)==1
 assert run(origin,'rev-parse','main')==before
 assert json.loads(out.read_text())['attempts']==[]


@pytest.mark.parametrize('remote_advanced',[False,True])
@pytest.mark.parametrize('name',m.FMS_FILES[2:])
def test_missing_projection_is_typed_refusal_before_any_push(fixture,remote_advanced,name):
 root,origin,peer,out=fixture;run(root,'rm',name);run(root,'commit','--amend','--no-edit')
 if remote_advanced:advance(peer)
 before=run(origin,'rev-parse','main')
 with pytest.raises(m.Refusal,match='fms_artifact'):
  m.persist(root,'main',out)
 assert run(origin,'rev-parse','main')==before and not out.exists()


def test_transplant_preserves_original_acquisition_author(fixture):
 root,origin,peer,out=fixture
 run(root,'commit','--amend','--no-edit','--author','Original Acquirer <original@example.invalid>')
 author=run(root,'show','-s','--format=%an|%ae|%aI','HEAD');advance(peer)
 assert m.persist(root,'main',out)==0
 assert run(origin,'show','-s','--format=%an|%ae|%aI','main')==author
