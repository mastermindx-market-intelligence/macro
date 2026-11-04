"""Inline optional metadata validation stays usable without helper acquisition."""
import copy
from pathlib import Path
import pytest
from scripts import agentos
from tests.test_agentos_direction_owner import workstream,decision


def files():
    rec=workstream();fid='a'*64;path='agentos/project-files/WS-DIRECTION-TEST/'+fid+'.txt'
    rec['artifacts']=[path];rec['project_files']=[{'file_id':fid,'artifact_ref':path,'display_name':'Notes.txt',
        'media_type':'text/plain','content_sha256':'b'*64,'origin':{'kind':'PRINCIPAL_UPLOAD',
        'actor_ref':'workspace:'+'c'*64,'request_sha256':'d'*64}}]
    return rec


def preference():
    rec=decision();rec.pop('direction');rec['key']='PROJECT-COMMUNICATION-PREFERENCE-DIRECTION-TEST'
    rec['answer']='Use brief plain-language updates.'
    rec['project_preference']={'schema':'agentos.project_preference.v1','work_ref':'WS:DIRECTION-TEST',
        'kind':'COMMUNICATION','value':rec['answer'],'origin':{'kind':'USER_EDIT','actor_ref':'workspace:'+'a'*64,
        'source_ref':None,'source_revision':None},'last_edit':{'actor_ref':'workspace:'+'b'*64,'request_sha256':'c'*64}}
    return rec


def ws_check(rec):return agentos.check_workstream(rec,Path('agentos/workstreams/WS-DIRECTION-TEST.md'),None)
def dec_check(rec):return agentos.check_decision(rec,Path('agentos/decisions/DEC-'+rec['key']+'.md'))


def test_real_inline_owner_accepts_declared_file_preference_without_loading_helpers(monkeypatch):
    ws,dec=files(),preference();before=copy.deepcopy((ws,dec))
    def forbidden(*args,**kwargs):pytest.fail('new helper import/acquisition in legacy owner')
    monkeypatch.setattr(Path,'open',forbidden)
    assert not any(p.hard for p in ws_check(ws))
    assert not any(p.hard for p in dec_check(dec))
    assert (ws,dec)==before


@pytest.mark.parametrize('change',['missing_index','duplicate','foreign_path','name_path','media','actor','origin','extra'])
def test_file_declaration_does_not_infer_source_membership_or_actor(change):
    rec=files();row=rec['project_files'][0]
    if change=='missing_index':rec['artifacts']=[]
    if change=='duplicate':rec['project_files']*=2
    if change=='foreign_path':row['artifact_ref']=row['artifact_ref'].replace('DIRECTION-TEST','FOREIGN')
    if change=='name_path':row['display_name']='../notes.txt'
    if change=='media':row['media_type']='text/html'
    if change=='actor':row['origin']['actor_ref']='Chairman'
    if change=='origin':row['origin']['kind']='INFERRED'
    if change=='extra':row['grant']=True
    assert any(p.hard and p.rule=='bad-project-files' for p in ws_check(rec))


@pytest.mark.parametrize('change',['value','scope','kind','conversation','actor','last_edit','extra'])
def test_preference_is_explicit_literal_scoped_source_not_generated_memory(change):
    rec=preference();row=rec['project_preference']
    if change=='value':row['value']='Not the actual answer'
    if change=='scope':row['work_ref']='WS:OTHER'
    if change=='kind':row['kind']='MODEL_MEMORY'
    if change=='conversation':row['origin']['kind']='CONVERSATION'
    if change=='actor':row['last_edit']['actor_ref']='Chairman'
    if change=='last_edit':row['last_edit']['request_sha256']='invalid'
    if change=='extra':row['active']=True
    assert any(p.hard and p.rule=='bad-project-preference' for p in dec_check(rec))


@pytest.mark.parametrize('instructions',[[],[{'instruction_ref':'INS:TEST','text':'  原文\nLiteral instruction  '}],
    [{'instruction_ref':'INS:TEST','text':'中'*4096}]])
def test_explicit_empty_and_verbatim_codepoint_bound_are_valid(instructions):
    rec=workstream();rec['standing_instructions']=instructions
    assert not any(p.hard for p in ws_check(rec))
    assert rec['standing_instructions']==instructions


@pytest.mark.parametrize('instructions',[None,{},[{'instruction_ref':'INS:TEST','text':'   '}],
    [{'instruction_ref':'INS:../path','text':'Literal'}],[{'instruction_ref':'INS:TEST','text':'中'*4097}],
    [{'instruction_ref':'INS:TEST','text':'Literal','revision':'a'*64}],
    [{'instruction_ref':'INS:TEST','text':'One'},{'instruction_ref':'INS:TEST','text':'Two'}]])
def test_instruction_revision_state_and_duplicates_cannot_be_authored(instructions):
    rec=workstream();rec['standing_instructions']=instructions
    assert any(p.hard and p.rule=='bad-standing-instructions' for p in ws_check(rec))
